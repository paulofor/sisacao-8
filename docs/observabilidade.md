# Observabilidade — Sprint 4

## 1. Formato de logs estruturados

Todas as funções do pipeline emitem um JSON único por execução com os campos:

| Campo | Descrição |
|-------|-----------|
| `job_name` | Nome lógico do job (`get_stock_data`, `dq_checks`, etc.). |
| `run_id` | UUID por execução (útil para correlacionar incidentes). |
| `status` | `STARTED`, `OK`, `WARN` ou `ERROR`. |
| `message` | Resumo legível do evento. |
| `date_ref` / `valid_for` | Datas processadas. |
| Métricas específicas | `tickers_with_data`, `rows_inserted`, `failures`, etc. |

Exemplo (Cloud Logging → filtro `textPayload:"job_name": "eod_signals"`):
```json
{"timestamp":"2024-08-12T22:05:31.087203+00:00","job_name":"eod_signals","run_id":"1d7b...","status":"OK","message":"Sinais EOD armazenados","date_ref":"2024-08-12","valid_for":"2024-08-13","generated":5,"table":"ingestaokraken.cotacao_intraday.sinais_eod"}
```

## 2. Alertas recomendados

### 2.1 Falha de execução
1. Criar uma *Log-based Metric* (`job_errors`) com o filtro:
   ```
   resource.type=("cloud_function" OR "cloud_run_revision")
   AND textPayload:"\"status\": \"ERROR\""
   ```
2. Em Cloud Monitoring → Alertes, criar política disparando quando
   `job_errors` > 0 em 5 minutos. Notificar por e-mail/Slack.

### 2.2 Pipeline silencioso
Crie uma métrica por job (`eod_signals_ok`, `backtest_ok`, ...):
```
resource.type=cloud_function
AND textPayload:"job_name\": \"eod_signals\""
AND textPayload:"\"status\": \"OK\""
```
Configure um alerta "Métrica ausente" se nenhuma série for registrada nas
últimas 24h.

### 2.3 Anomalias de dados
Use `dq_checks_daily`:
```sql
SELECT check_name, status, details
FROM `ingestaokraken.cotacao_intraday.dq_checks_daily`
WHERE status = 'FAIL'
  AND check_date >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 7 DAY);
```
Automatize um alerta (Scheduled Query + Pub/Sub ou Dataform) que dispara quando
`status = 'FAIL'`. Utilize também `dq_incidents` para acompanhamento manual.

## 3. Dashboard / Looker Studio

Monte um painel simples com:
- `vw_pipeline_status` para status geral.
- Série temporal de `rows_today` por componente.
- Tabela de `dq_checks_daily` destacando últimos resultados.
- Top 5 sinais do dia (`sinais_eod` ordenados por `score`).

## 4. Runbook de alertas

| Alerta | Ação |
|--------|------|
| `job_errors` | Abrir log pelo `run_id`, reprocessar job (ver `RUNBOOK.md`). |
| Pipeline silencioso | Executar job manualmente; se feriado, registrar motivo. |
| `dq_checks_daily: FAIL` | Consultar `details`, corrigir fonte (diário/intraday/sinais) e reexecutar `dq_checks`. |

Mantendo esses alertas ativos e revisando trimestralmente as métricas, o time
passa a ser notificado rapidamente sobre falhas ou ausência de dados.
