# Backtest audit (2026-04-30)

Fonte: MCP Server (`/mcp`) via JSON-RPC.

## Resumo

- Não há erros recentes da função `backtest_daily` (janela de 168h, severidade `ERROR`, `row_count = 0`).
- Os logs retornados em severidade `DEFAULT` para `backtest_daily` são eventos de **deploy/update** (AuditLog), não execuções de request.
- Tabelas do backtest estão vazias:
  - `cotacao_intraday.backtest_trades`: `0` linhas.
  - `cotacao_intraday.backtest_metrics`: `0` linhas.
- A tabela de sinais **não** está vazia:
  - `cotacao_intraday.sinais_eod`: `80` linhas; última modificação em `2026-04-30T01:00:11.701Z`.

## Evidências coletadas

- `cloud_run_function_logs(function_name="backtest_daily", severity="ERROR", hours=168, limit=20)` retornou `row_count = 0`.
- `bigquery_query("SELECT COUNT(*) AS trades_count FROM ...backtest_trades")` retornou `0`.
- `bigquery_query("SELECT COUNT(*) AS metrics_count FROM ...backtest_metrics")` retornou `0`.
- `bigquery_query("SELECT valid_for, COUNT(*) ... FROM ...sinais_eod ...")` retornou sinais até `2026-04-29`.
- `bigquery_query("SELECT table_id, row_count, last_modified ... __TABLES__ ...")`:
  - `backtest_metrics`: `row_count=0`, `last_modified=2026-02-26T02:51:39.808Z`
  - `backtest_trades`: `row_count=0`, `last_modified=2026-04-22T01:15:14.972Z`
  - `sinais_eod`: `row_count=80`, `last_modified=2026-04-30T01:00:11.701Z`

## Hipótese principal

A ingestão de sinais está funcionando, porém a execução da função `backtest_daily` não está gravando nas tabelas de destino (ou não está sendo acionada no fluxo esperado). Como não há erro no recorte consultado, é provável que haja:

1. ausência/erro no gatilho de execução (scheduler/workflow);
2. execução sem dados elegíveis por regra de data/feriado na função;
3. escrita em tabela/projeto diferente por variável de ambiente divergente;
4. falha silenciosa sem log de erro (tratamento que retorna sucesso sem insert).

## Próximos passos sugeridos

1. Consultar logs de execução por `INFO/NOTICE` filtrando `resource.type=cloud_run_revision` e `service_name` da revisão ativa.
2. Forçar uma execução manual HTTP da função `backtest_daily` com payload de data conhecida com sinais (ex.: `valid_for=2026-04-29`) e validar resposta.
3. Verificar variáveis efetivas de runtime da função (`BQ_BACKTEST_TRADES_TABLE`, `BQ_BACKTEST_METRICS_TABLE`, `GCP_PROJECT`, dataset).
4. Conferir IAM de escrita BigQuery para a service account da função.
