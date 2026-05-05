
# Registros — Evolução Funções

> Orientação: todos os registros deste documento devem sempre incluir **data e hora no fuso UTC-3**.
> Neste documento segue política de **append-only** (não pode ter nenhuma linha apagada; apenas inserções).

## 2026-05-05 08:35 UTC-3 — MCP Server (logs de execução)

- Ajustada a tool `cloud_run_function_logs` em `mcp-server/src/server.py` para reduzir ruído de auditoria por padrão:
  - novo parâmetro `include_audit_logs` (default `False`);
  - quando `False`, exclui `cloudaudit.googleapis.com/activity` e `cloudaudit.googleapis.com/data_access`.
- Mantida a compatibilidade de nomes com hífen/underscore para localizar logs de runtime com maior precisão.
- Objetivo operacional: priorizar logs de invocação/execução e evitar retorno predominante de eventos administrativos de deploy.

## 2026-05-05 09:05 UTC-3 — Correção `backtest_daily` (serialização JSON)

- Corrigida a persistência no BigQuery da função `backtest_daily` para evitar erro `TypeError: Object of type date is not JSON serializable` durante `load_table_from_json`.
- Implementada normalização de payload antes da carga, convertendo automaticamente campos `datetime.date` e `datetime.datetime` para `ISO-8601` (`YYYY-MM-DD` e timestamp ISO).
- A correção foi aplicada no fluxo genérico de `_load_table`, cobrindo tanto gravação de `backtest_trades` quanto de `backtest_metrics`.
