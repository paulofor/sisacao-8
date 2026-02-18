# Runbook operacional — Sisacao-8 (Sprint 4)

Este documento descreve como operar o pipeline diariamente, o que checar em
caso de incidentes e como reprocessar um dia específico utilizando as funções
serverless disponíveis no GCP.

## 1. Checklist diário (até 22h BRT)

1. **Verificar o painel `vw_pipeline_status`:**
   ```sql
   SELECT *
   FROM `ingestaokraken.cotacao_intraday.vw_pipeline_status`
   ORDER BY component;
   ```
   - Todos os componentes devem ter `last_reference` = pregão do dia.
   - `rows_today = 0` indica ausência de carga para a data corrente.

2. **Confirmar DQ:**
   ```sql
   SELECT check_name, status, details
   FROM `ingestaokraken.cotacao_intraday.dq_checks_daily`
   WHERE check_date = CURRENT_DATE('America/Sao_Paulo')
   ORDER BY check_name;
   ```
   Qualquer `status = 'FAIL'` deve gerar incidente (ver seção 3).

3. **Monitorar logs estruturados:**
   - Filtrar no Cloud Logging: `textPayload:"\"job_name\": \"eod_signals\""`.
   - Conferir se existe log `status":"OK"` para cada job (`google_finance_price`,
     `get_stock_data`, `intraday_candles`, `eod_signals`, `backtest_daily`,
     `dq_checks`, `alerts`).

4. **Alertas enviados:** conferir o canal (Telegram ou equivalente) após o
   job `alerts-diario`. Em caso de ausência, executar a função manualmente (ver
   seção 2).

## 2. Reprocessamentos idempotentes

Todos os jobs recebem o parâmetro `date=YYYY-MM-DD` via querystring.
Utilize `gcloud functions call` ou a aba “Testing” do console.

1. **Diário oficial (`get_stock_data`):**
   ```bash
   gcloud functions call get_stock_data \
     --data '{}'
   ```
   - Reprocessa a data atual. Para datas passadas, defina
     `{"date": "2024-08-12"}`.
   - A função realiza `DELETE`/`MERGE` por partição, portanto é segura.

2. **Candles intraday (`intraday_candles`):**
   ```bash
   gcloud functions call intraday_candles \
     --data '{"date": "2024-08-12"}'
   ```
   - Regera `candles_intraday_15m` e `candles_intraday_1h` para o dia informado.

3. **Sinais (`eod_signals`):**
   ```bash
   gcloud functions call eod_signals \
     --data '{"date": "2024-08-12"}'
   ```
   - Gera até 5 sinais para o pregão informado e sobrescreve a partição.

4. **Backtest (`backtest_daily`):**
   ```bash
   gcloud functions call backtest_daily \
     --data '{"date": "2024-08-12"}'
   ```
   - Recria `backtest_trades` e `backtest_metrics` da data.

5. **DQ (`dq_checks`):**
   ```bash
   gcloud functions call dq_checks \
     --data '{"date": "2024-08-12"}'
   ```
   - Útil após reprocessar qualquer etapa; confirma que `dq_checks_daily` ficou
     com `status = PASS`.

## 3. Tratamento de incidentes

1. **Falha em job:**
   - Verificar o log estruturado correspondente (`status = "ERROR"`).
   - Identificar o `run_id` e consultar o campo `diagnostics`/`reason`.
   - Reprocessar o job (seção 2) e confirmar alerta automático.

2. **DQ `FAIL`:**
   - Consultar `dq_incidents` para identificar o `details` do check.
   - Corrigir a causa (ex.: reprocessar `get_stock_data` se `daily_freshness`
     falhar).
   - Reexecutar `dq_checks` para fechar o incidente.

3. **Pipeline silencioso:**
   - `intraday` sem dados recentes: disparar manualmente `google_finance_price`
     e validar `cotacao_b3`.
   - `sinais_eod` vazios após 22h: conferir se houve feriado. Se não, executar a
     função manualmente.

## 4. Runbook rápido por componente

| Componente | Indicadores | Logs (filtro) | Reprocesso |
|------------|-------------|---------------|------------|
| `google_finance_price` | `cotacao_b3` última hora >= 17:45 | `job_name="google_finance_price"` | `gcloud run jobs execute ...` ou função HTTP |
| `get_stock_data` | `cotacao_ohlcv_diario` com pregão atual | `job_name="get_stock_data"` | `gcloud functions call get_stock_data` |
| `intraday_candles` | `candles_intraday_15m` com linhas para o dia | `job_name="intraday_candles"` | `gcloud functions call intraday_candles` |
| `eod_signals` | `sinais_eod` <= 5 linhas/dia | `job_name="eod_signals"` | `gcloud functions call eod_signals` |
| `backtest_daily` | `backtest_metrics.as_of_date = date_ref` | `job_name="backtest_daily"` | `gcloud functions call backtest_daily` |
| `dq_checks` | `dq_checks_daily` status PASS | `job_name="dq_checks"` | `gcloud functions call dq_checks` |
| `alerts` | Mensagem no canal (Telegram) | `job_name="alerts"` | `gcloud functions call alerts` |

## 5. Comunicação

- **Falhas críticas**: abrir incidente no canal definido pelo time (Slack ou
  PagerDuty) e anexar o `run_id` do log estruturado.
- **Mudanças de configuração**: atualizar `infra/bq/01_config_tables.sql`
  (tickers/feriados) e documentar no PR.

Seguindo estes passos o ambiente pode ser recriado do zero e operado por qualquer
membro do time sem dependência de conhecimento tácito.
