"""MCP Server do sisacao-8 com transporte remoto via HTTP.

Este servidor é intencionalmente enxuto nesta etapa: registra apenas
ferramentas de diagnóstico para confirmar disponibilidade remota.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_TRANSPORT = "streamable-http"


def _runtime_config() -> Dict[str, Any]:
    """Carrega configuração de runtime a partir de variáveis de ambiente."""
    project = os.getenv("GCP_PROJECT", "ingestaokraken")
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

    return server


def main() -> None:
    load_dotenv()
    config = _runtime_config()

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
