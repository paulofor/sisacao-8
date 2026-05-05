from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud import logging as cloud_logging
from google.oauth2 import service_account
from mcp.server.fastmcp import FastMCP

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 80
DEFAULT_TRANSPORT = "streamable-http"
DEFAULT_QUERY_MAX_ROWS = 200
READ_ONLY_SQL_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)

LOGGER = logging.getLogger("sisacao8.mcp_server")


def _extract_log_message(payload: Any) -> str:
    """Extrai uma mensagem legível a partir do payload do Cloud Logging."""
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for key in ("message", "textPayload"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return json.dumps(payload, ensure_ascii=False)

    return str(payload)


def _format_log_line(timestamp: Any, message: str) -> str:
    """Formata linha legível de log em padrão próximo ao comando gcloud."""
    ts = str(timestamp)
    if "T" in ts:
        ts = ts.replace("T", " ")
    if "+" in ts:
        ts = ts.split("+", maxsplit=1)[0]
    if ts.endswith("Z"):
        ts = ts[:-1]
    if "." in ts:
        ts = ts.split(".", maxsplit=1)[0]
    return f"{ts} {message}".rstrip()


def _normalize_project(project: str) -> str:
    """Normaliza project id para o formato esperado no BigQuery."""
    normalized = (project or "").strip().lower()
    return normalized or "ingestaokraken"


def _runtime_config() -> Dict[str, Any]:
    """Carrega configuração de runtime a partir de variáveis de ambiente."""
    project = _normalize_project(os.getenv("GCP_PROJECT", "ingestaokraken"))
    region = os.getenv("GCP_REGION", "us-east1")
    host = os.getenv("MCP_HOST", DEFAULT_HOST)
    port = int(os.getenv("MCP_PORT", str(DEFAULT_PORT)))
    transport = os.getenv("MCP_TRANSPORT", DEFAULT_TRANSPORT)

    return {
        "project": project,
        "region": region,
        "host": host,
        "port": port,
        "transport": transport,
    }


def _load_service_account_info() -> Optional[Dict[str, Any]]:
    """Carrega credenciais no mesmo padrão usado pelo backend Java."""
    raw_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        LOGGER.info("Credencial carregada de GCP_SERVICE_ACCOUNT_JSON")
        return json.loads(raw_json)

    raw_base64 = os.getenv("GCP_SERVICE_ACCOUNT_JSON_BASE64", "").strip()
    if raw_base64:
        LOGGER.info("Credencial carregada de GCP_SERVICE_ACCOUNT_JSON_BASE64")
        decoded = base64.b64decode(raw_base64).decode("utf-8")
        return json.loads(decoded)

    location = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if location:
        credentials_path = os.path.abspath(location)
        exists = os.path.exists(credentials_path)
        readable = os.access(credentials_path, os.R_OK) if exists else False
        LOGGER.info(
            "GOOGLE_APPLICATION_CREDENTIALS detectado: %s | exists=%s | readable=%s",
            credentials_path,
            exists,
            readable,
        )
        if not exists:
            raise FileNotFoundError(
                f"Arquivo de credenciais não encontrado: {credentials_path}"
            )
        if not readable:
            raise PermissionError(
                "Sem permissão de leitura no arquivo de credenciais: "
                f"{credentials_path}"
            )
        with open(credentials_path, "r", encoding="utf-8") as credentials_file:
            return json.load(credentials_file)

    fallback_path = "/opt/sisacao/chaves/codex.json"
    fallback_exists = os.path.exists(fallback_path)
    fallback_readable = os.access(fallback_path, os.R_OK) if fallback_exists else False
    LOGGER.info(
        "Fallback credentials path: %s | exists=%s | readable=%s",
        fallback_path,
        fallback_exists,
        fallback_readable,
    )
    if fallback_exists and fallback_readable:
        with open(fallback_path, "r", encoding="utf-8") as credentials_file:
            LOGGER.info(
                "Credencial carregada do fallback /opt/sisacao/chaves/codex.json"
            )
            return json.load(credentials_file)

    LOGGER.warning("Nenhuma credencial explícita encontrada; usando ADC padrão")
    return None


def _build_bigquery_client(project: str) -> bigquery.Client:
    """Cria cliente BigQuery com fallback para ADC sem credencial explícita."""
    service_account_info = _load_service_account_info()
    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        return bigquery.Client(project=project, credentials=credentials)

    return bigquery.Client(project=project)


def _build_logging_client(project: str) -> cloud_logging.Client:
    """Cria cliente Cloud Logging com o mesmo fluxo de credenciais do BigQuery."""
    service_account_info = _load_service_account_info()
    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        return cloud_logging.Client(project=project, credentials=credentials)

    return cloud_logging.Client(project=project)


def _read_logs_with_gcloud(
    *,
    project: str,
    region: str,
    service_name: str,
    limit: int,
    hours: int,
    severity: str,
    include_audit_logs: bool,
) -> Dict[str, Any]:
    """Executa `gcloud run services logs read` e retorna linhas normalizadas."""
    cmd = [
        "gcloud",
        "run",
        "services",
        "logs",
        "read",
        service_name,
        "--region",
        region,
        "--project",
        project,
        "--freshness",
        f"{hours}h",
        "--limit",
        str(limit),
        "--format",
        "value(timestamp,textPayload)",
    ]
    log_filter_parts: List[str] = []
    if severity != "DEFAULT":
        log_filter_parts.append(f"severity>={severity}")
    if not include_audit_logs:
        log_filter_parts.append(
            'logName !~ "cloudaudit.googleapis.com%2F(activity|data_access)"'
        )
    if log_filter_parts:
        cmd.extend(["--log-filter", " AND ".join(log_filter_parts)])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "falha ao executar gcloud")

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "source": "gcloud",
        "command": " ".join(cmd),
        "lines": lines,
        "output": "\n".join(lines),
    }


def build_server(config: Dict[str, Any]) -> FastMCP:
    """Instancia e configura o servidor MCP."""
    server = FastMCP(
        name="sisacao-8-mcp-server",
        instructions=(
            "Servidor MCP operacional do sisacao-8 para consultas operacionais "
            "de mercado, BigQuery e observabilidade."
        ),
        host=config["host"],
        port=config["port"],
        streamable_http_path="/mcp",
    )

    @server.tool(name="ping")
    def ping() -> Dict[str, str]:
        """Ferramenta de diagnóstico para validar disponibilidade remota."""
        return {"status": "ok"}

    @server.tool(name="runtime_config")
    def runtime_config() -> Dict[str, str]:
        """Expõe configurações não sensíveis carregadas no runtime."""
        return {
            "project": str(config["project"]),
            "region": str(config["region"]),
            "transport": str(config["transport"]),
            "host": str(config["host"]),
            "port": str(config["port"]),
        }

    @server.tool(name="bigquery_access_check")
    def bigquery_access_check() -> Dict[str, str]:
        """Valida autenticação e execução de query simples no BigQuery."""
        try:
            client = _build_bigquery_client(project=str(config["project"]))
            query_job = client.query("SELECT 1 AS ok")
            rows = list(query_job.result(timeout=30))
            ok_value = rows[0]["ok"] if rows else None
            return {
                "status": "ok",
                "project": str(config["project"]),
                "query_result": str(ok_value),
            }
        except Exception as exc:  # pragma: no cover - diagnóstico operacional.
            return {
                "status": "error",
                "project": str(config["project"]),
                "message": str(exc),
            }

    @server.tool(name="bigquery_query")
    def bigquery_query(
        sql: str, max_rows: int = DEFAULT_QUERY_MAX_ROWS
    ) -> Dict[str, Any]:
        """
        Executa query read-only no BigQuery com limite de linhas no resultado.

        Regras de segurança:
        - aceita apenas queries iniciadas em SELECT/WITH;
        - bloqueia múltiplas instruções separadas por ';'.
        """
        normalized = sql.strip()
        if not normalized:
            return {"status": "error", "message": "sql vazio"}

        if ";" in normalized.rstrip(";"):
            return {
                "status": "error",
                "message": "múltiplas instruções SQL não são permitidas",
            }

        if not READ_ONLY_SQL_PATTERN.match(normalized):
            return {
                "status": "error",
                "message": "apenas queries read-only iniciadas com SELECT ou WITH",
            }

        safe_max_rows = max(1, min(int(max_rows), 2000))

        try:
            client = _build_bigquery_client(project=str(config["project"]))
            query_job = client.query(normalized)
            rows_iter = query_job.result(timeout=60)
            rows = [dict(row.items()) for row in rows_iter][:safe_max_rows]
            return {
                "status": "ok",
                "project": str(config["project"]),
                "row_count": len(rows),
                "max_rows": safe_max_rows,
                "rows": rows,
            }
        except Exception as exc:  # pragma: no cover - diagnóstico operacional.
            return {
                "status": "error",
                "project": str(config["project"]),
                "message": str(exc),
            }

    @server.tool(name="cloud_run_function_logs")
    def cloud_run_function_logs(
        function_name: str,
        severity: str = "DEFAULT",
        limit: int = 50,
        order_by: str = "timestamp desc",
        hours: int = 24,
        include_audit_logs: bool = False,
        gcloud_style: bool = True,
        use_gcloud_cli: bool = True,
    ) -> Dict[str, Any]:
        """Consulta logs de uma Cloud Run Function por nome e janela de tempo."""
        normalized_function = function_name.strip()
        if not normalized_function:
            return {"status": "error", "message": "function_name vazio"}

        service_candidates = [normalized_function]
        hyphenated = normalized_function.replace("_", "-")
        underscored = normalized_function.replace("-", "_")
        for candidate in (hyphenated, underscored):
            if candidate not in service_candidates:
                service_candidates.append(candidate)

        normalized_severity = severity.strip().upper() or "DEFAULT"
        safe_limit = max(1, min(int(limit), 200))
        safe_hours = max(1, min(int(hours), 168))
        safe_order = (
            "timestamp asc"
            if order_by.strip().lower() == "timestamp asc"
            else "timestamp desc"
        )

        window_start = datetime.now(timezone.utc) - timedelta(hours=safe_hours)
        window_start_rfc3339 = window_start.isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )

        service_filter = " OR ".join(
            [
                (
                    'resource.type="cloud_run_revision" '
                    f'AND resource.labels.service_name="{candidate}"'
                )
                for candidate in service_candidates
            ]
        )
        function_filter = " OR ".join(
            [
                (
                    'resource.type="cloud_function" '
                    f'AND resource.labels.function_name="{candidate}"'
                )
                for candidate in service_candidates
            ]
        )
        filter_parts = [
            f"({service_filter} OR {function_filter})",
            f'timestamp >= "{window_start_rfc3339}"',
        ]
        if not include_audit_logs:
            filter_parts.append(
                'logName !~ "cloudaudit.googleapis.com%2F(activity|data_access)"'
            )
        if normalized_severity != "DEFAULT":
            filter_parts.append(f"severity>={normalized_severity}")
        logs_filter = "\n".join(filter_parts)

        if use_gcloud_cli:
            try:
                gcloud_service = service_candidates[0]
                if hyphenated in service_candidates:
                    gcloud_service = hyphenated
                gcloud_response = _read_logs_with_gcloud(
                    project=str(config["project"]),
                    region=str(config["region"]),
                    service_name=gcloud_service,
                    limit=safe_limit,
                    hours=safe_hours,
                    severity=normalized_severity,
                    include_audit_logs=include_audit_logs,
                )
                return {
                    "status": "ok",
                    "project": str(config["project"]),
                    "function_name": normalized_function,
                    "severity": normalized_severity,
                    "hours": safe_hours,
                    "include_audit_logs": include_audit_logs,
                    "order_by": safe_order,
                    "row_count": len(gcloud_response["lines"]),
                    "entries": [],
                    "lines": gcloud_response["lines"],
                    "output": gcloud_response["output"] if gcloud_style else None,
                    "source": gcloud_response["source"],
                    "command": gcloud_response["command"],
                }
            except Exception as exc:
                LOGGER.warning(
                    "Falha ao buscar logs via gcloud CLI; fallback para API. erro=%s",
                    exc,
                )

        try:
            client = _build_logging_client(project=str(config["project"]))
            entries_iter = client.list_entries(
                filter_=logs_filter,
                order_by=safe_order,
                page_size=safe_limit,
            )

            entries = []
            formatted_lines: List[str] = []
            for entry in entries_iter:
                message = _extract_log_message(entry.payload)
                formatted_line = _format_log_line(entry.timestamp, message)
                formatted_lines.append(formatted_line)

                entries.append(
                    {
                        "timestamp": str(entry.timestamp),
                        "severity": str(entry.severity),
                        "log_name": str(entry.log_name),
                        "insert_id": str(entry.insert_id),
                        "message": str(message),
                    }
                )
                if len(entries) >= safe_limit:
                    break

            return {
                "status": "ok",
                "project": str(config["project"]),
                "function_name": normalized_function,
                "severity": normalized_severity,
                "hours": safe_hours,
                "include_audit_logs": include_audit_logs,
                "order_by": safe_order,
                "row_count": len(entries),
                "entries": entries,
                "lines": formatted_lines,
                "output": "\n".join(formatted_lines) if gcloud_style else None,
                "source": "cloud_logging_api",
            }
        except Exception as exc:  # pragma: no cover - diagnóstico operacional.
            return {
                "status": "error",
                "project": str(config["project"]),
                "message": str(exc),
            }

    return server


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    load_dotenv()
    config = _runtime_config()

    LOGGER.info(
        "Runtime config carregada | project=%s | region=%s | host=%s "
        "| port=%s | transport=%s",
        config["project"],
        config["region"],
        config["host"],
        config["port"],
        config["transport"],
    )
    _load_service_account_info()

    server = build_server(config)

    print("[mcp-server] servidor inicializado")
    print(f"[mcp-server] projeto: {config['project']}")
    print(f"[mcp-server] região: {config['region']}")
    print(
        "[mcp-server] escutando em "
        f"{config['host']}:{config['port']} via {config['transport']}"
    )

    server.run(transport=config["transport"])


if __name__ == "__main__":
    main()
