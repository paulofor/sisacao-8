"""Bootstrap inicial do MCP Server do sisacao-8.

Nesta fase o servidor ainda não registra ferramentas reais.
A implementação de acesso ao BigQuery e Cloud Logging será adicionada
em incrementos posteriores.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    project = os.getenv("GCP_PROJECT", "ingestaokraken")
    region = os.getenv("GCP_REGION", "us-east1")

    print("[mcp-server] bootstrap inicial carregado")
    print(f"[mcp-server] projeto: {project}")
    print(f"[mcp-server] região: {region}")
    print("[mcp-server] TODO: registrar tools MCP para BigQuery e Logs")


if __name__ == "__main__":
    main()
