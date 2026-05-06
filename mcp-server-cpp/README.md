# mcp-server-cpp

Versão C++ do MCP Server com as mesmas regras operacionais do `mcp-server` em Python:

- Endpoint HTTP `POST /mcp` (JSON-RPC 2.0).
- `initialize` retorna `mcp-session-id` e metadados do servidor.
- `tools/list` e `tools/call` exigem `mcp-session-id` válido.
- Credenciais GCP seguem a mesma precedência:
  1. `GCP_SERVICE_ACCOUNT_JSON`
  2. `GCP_SERVICE_ACCOUNT_JSON_BASE64`
  3. `GOOGLE_APPLICATION_CREDENTIALS`
  4. fallback `/opt/sisacao/chaves/codex.json`
  5. ADC padrão se nada for encontrado.
- `bigquery_query` aceita apenas SQL read-only iniciando com `SELECT` ou `WITH`.
- `cloud_run_function_logs` usa `gcloud run services logs read`.

## Build

```bash
cmake -S . -B build
cmake --build build
```

## Run

```bash
./build/mcp-server-cpp
```

Variáveis:
- `MCP_HOST` (default `0.0.0.0`)
- `MCP_PORT` (default `80`)
- `GCP_PROJECT` (default `ingestaokraken`)
- `GCP_REGION` (default `us-east1`)
