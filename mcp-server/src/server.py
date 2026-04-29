from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from mcp.server.fastmcp import FastMCP

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 80
DEFAULT_TRANSPORT = "streamable-http"
DEFAULT_QUERY_MAX_ROWS = 200
READ_ONLY_SQL_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)

LOGGER = logging.getLogger("sisacao8.mcp_server")


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
                f"Sem permissão de leitura no arquivo de credenciais: {credentials_path}"
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

    return server


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    load_dotenv()
    config = _runtime_config()

    LOGGER.info(
        "Runtime config carregada | project=%s | region=%s | host=%s | port=%s | transport=%s",
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
