# Verificação MCP Server → BigQuery (2026-04-29)

## Objetivo
Validar acesso ao MCP Server via **HTTP** no IP informado (`187.45.254.75`) e verificar
se a ferramenta de BigQuery consegue executar query.

## Fluxo validado (JSON-RPC)

1. `initialize` no endpoint `http://187.45.254.75/mcp`
2. `tools/list` para confirmar ferramentas expostas
3. `tools/call` com `bigquery_access_check`

## Comandos executados

```bash
# 1) initialize (com Accept obrigatório para streamable-http)
curl -sS -D - -o /tmp/mcp_newip_init2.out -X POST 'http://187.45.254.75/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codex-cli","version":"1.0"}}}'

# 2) tools/list (com mcp-session-id retornado no initialize)
curl -sS -D - -o /tmp/mcp_tools.out -X POST 'http://187.45.254.75/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: a3391494eb544648a2302348386724ab' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 3) bigquery_access_check
curl -sS -D - -o /tmp/mcp_bqcheck.out -X POST 'http://187.45.254.75/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: a3391494eb544648a2302348386724ab' \
  --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"bigquery_access_check","arguments":{}}}'
```

## Resultado observado
- O MCP Server respondeu `initialize` com sucesso (`HTTP 200` + `text/event-stream`) e criou sessão MCP.
- `tools/list` funcionou e retornou as ferramentas: `ping`, `runtime_config`, `bigquery_access_check`, `bigquery_query`.
- A chamada `bigquery_access_check` chegou ao BigQuery, porém retornou erro de configuração de projeto:
  - `400 ... ProjectId must be non-empty`
  - projeto reportado na resposta: `IngestaoKraken`

## Conclusão
- **Conectividade MCP validada via HTTP no IP `187.45.254.75`.**
- **A query no BigQuery ainda não executa com sucesso** devido a configuração inválida de projeto no runtime do servidor MCP.

## Próximo ajuste recomendado
Corrigir o `project`/credencial do BigQuery no ambiente do MCP Server (valor esperado: `ingestaokraken`) e repetir `tools/call` com `bigquery_access_check`.
