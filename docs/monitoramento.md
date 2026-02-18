# Monitoramento operacional (Sprint 4)

O monitoramento da Sprint 4 combina **logs estruturados**, **views no BigQuery**
 e **data-quality checks** automáticos.

## 1. Visão consolidada no BigQuery

A view `cotacao_intraday.vw_pipeline_status` resume o status diário:

```sql
SELECT *
FROM `ingestaokraken.cotacao_intraday.vw_pipeline_status`
ORDER BY component;
```

| Componente | Interpretação |
|------------|---------------|
| `cotacao_ohlcv_diario` | Último pregão disponível via `get_stock_data`. |
| `cotacao_b3` | Última hora capturada pelo `google_finance_price`. |
| `sinais_eod` | Data e quantidade de sinais gerados. |
| `backtest_metrics` | `as_of_date` mais recente após o backtest diário. |
| `dq_checks_daily` | Última execução dos checks automáticos. |

Use a view em dashboards Looker Studio para alimentar gráficos de status.

## 2. Data Quality

A função `dq_checks` grava resultados em `dq_checks_daily` e abre incidentes
em `dq_incidents` quando `status = FAIL`.

```sql
SELECT check_name, status, details
FROM `ingestaokraken.cotacao_intraday.dq_checks_daily`
WHERE check_date = CURRENT_DATE('America/Sao_Paulo')
ORDER BY check_name;
```

Checks implementados:
- `daily_freshness`: cobertura de tickers no diário oficial.
- `intraday_freshness`: hora mais recente por ticker no intraday.
- `daily_uniqueness` e `ohlc_validity`: validações de integridade.
- `signals_limits`: máximo de 5 sinais e consistência de target/stop.
- `backtest_metrics`: garante métricas do dia.

## 3. Logs estruturados

Consulte `docs/observabilidade.md` para o formato completo. Exemplos de filtros
no Cloud Logging:

- Falhas de qualquer job:
  ```
  resource.type=("cloud_function" OR "cloud_run_revision")
  AND textPayload:"\"status\": \"ERROR\""
  ```
- Execuções bem-sucedidas do backtest:
  ```
  textPayload:"job_name\": \"backtest_daily\""
  AND textPayload:"\"status\": \"OK\""
  ```

## 4. Checklists e runbook

Consulte [`RUNBOOK.md`](../RUNBOOK.md) para o checklist diário, procedimentos de
reprocessamento e ações recomendadas quando um alerta dispara.

## 5. Alertas sugeridos

1. **Falha de execução:** log-based metric em `status="ERROR"`.  
2. **Pipeline silencioso:** métrica de `status="OK"` ausente por >24h.  
3. **DQ FAIL:** scheduled query em `dq_checks_daily` + notificação.

Com essas peças publicadas, um operador consegue validar o dia em poucos
minutos e agir rapidamente em caso de incidentes.
