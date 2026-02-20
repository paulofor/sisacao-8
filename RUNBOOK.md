# Runbook operacional — Sisacao-8 (Sprint 5)

Este runbook descreve o checklist diário, a rotina de reprocessamento e as
respostas esperadas para cada alerta configurado na Sprint 5. Todos os jobs são
privados por padrão (Cloud Functions/Run com IAM) e precisam ser invocados com
service accounts dedicadas.

## 1. Checklist diário (até 22h BRT)

1. **Status agregados (`vw_pipeline_status`)**
   ```sql
   SELECT *
   FROM `ingestaokraken.cotacao_intraday.vw_pipeline_status`
   ORDER BY component;
   ```
   - `last_reference` deve coincidir com o pregão mais recente.
   - `rows_today = 0` indica silêncio e abre alerta em Cloud Monitoring.

2. **Data quality (`dq_checks_daily`)**
   ```sql
   SELECT check_name, status, details
   FROM `ingestaokraken.cotacao_intraday.dq_checks_daily`
   WHERE check_date = CURRENT_DATE('America/Sao_Paulo')
   ORDER BY check_name;
   ```
   - Falhas em `daily_freshness`, `intraday_freshness`, `intraday_uniqueness`,
     `signals_freshness` ou `backtest_metrics` exigem incidente imediato.
   - Verifique o `config_version` registrado para confirmar qual conjunto de
     thresholds estava ativo.

3. **Alertas no Cloud Monitoring**
   - Painel: `Monitoring → Alerting`. Os Terraform em `infra/monitoring/`
     criam políticas para:
     - Erros de job (`sisacao_job_error`).
     - Falha de DQ (`sisacao_dq_fail`).
     - Falha no download COTAHIST.
     - Silêncio de `get_stock_data`, `intraday_candles` e `eod_signals`.
   - Cada alerta contém o `run_id` para cruzar com Cloud Logging.

4. **Logs estruturados**
   - Filtro sugerido: `jsonPayload.job_name="eod_signals" AND jsonPayload.status`.
   - Confirmar que cada execução guarda `reason`, `mode`, `force` e
     `config_version` para auditoria.

## 2. Reprocessamento autenticado

Utilize `tools/reprocess.py` para acionar a cadeia completa com ID token (SA
invoker). O script respeita `mode`, `date_ref`, `force` e registra
`reason=manual_reprocess` por padrão.

```bash
python tools/reprocess.py 2024-08-12 \
  --project ingestaokraken \
  --region us-central1 \
  --service-account-key sa-invoker.json \
  --mode ALL \
  --force
```

Modos disponíveis:
- `DAILY`: apenas `get_stock_data`.
- `EOD`: `get_stock_data` → `intraday_candles` → `eod_signals`.
- `BACKTEST`: somente `backtest_daily`.
- `ALL` (default): cadeia completa + `dq_checks`.

Sempre inclua o motivo real via `--reason` quando for diferente de
`manual_reprocess`. O parâmetro `--force` ignora o cutoff (18h) e validações de
feriado — use somente após avaliar o impacto no `RUNBOOK`.

## 3. Tratamento de incidentes

| Alerta / Check                   | Ação imediata                                                                 |
|----------------------------------|-------------------------------------------------------------------------------|
| `sisacao_job_error`              | Abrir o log pelo `run_id`, identificar o estágio e reprocessar com o script. |
| `sisacao_dq_fail`                | Consultar `dq_incidents` e corrigir o componente afetado, depois reexecutar DQ. |
| `sisacao_cotahist_failure`       | Verificar conectividade com B3, validar `allow_offline_fallback` no `pipeline_config` e reprocessar assim que normalizar. |
| `silêncio get_stock_data`        | Reprocessar DAILY; checar se havia feriado ou se o Scheduler perdeu a janela. |
| `silêncio intraday_candles`      | Verificar ingestão intraday (`cotacao_b3`) e reprocessar o dia.               |
| `silêncio eod_signals`           | Confirmar se `parametros_estrategia` estavam ativos e executar `--mode EOD`.  |
| `signals_freshness = FAIL`       | Sinais não chegaram até 22h+grace. Rodar `eod_signals` manualmente e avisar trading. |
| `backtest_metrics = FAIL`        | Falta de métricas ou execução pós-deadline. Reprocessar backtest e validar logs. |

Após reprocessar, registre o incidente no canal do time informando `run_id`,
`config_version` e motivo.

## 4. Componentes de referência

| Componente          | Indicadores principais                                                   | Log (filtro)                                 | Reprocesso                           |
|---------------------|---------------------------------------------------------------------------|----------------------------------------------|--------------------------------------|
| `get_stock_data`    | `cotacao_ohlcv_diario` atualizado + alerta `silence` limpo               | `job_name="get_stock_data"`                 | `python tools/reprocess.py ... --mode DAILY` |
| `intraday_candles`  | `candles_intraday_*` do dia + alerta de silêncio limpo                   | `job_name="intraday_candles"`               | `--mode EOD` ou `ALL`                |
| `eod_signals`       | `sinais_eod` com `config_version` esperado; `signals_freshness=PASS`     | `job_name="eod_signals"`                   | `--mode EOD` ou `ALL`                |
| `backtest_daily`    | `backtest_metrics.as_of_date` = pregão, sem atraso                       | `job_name="backtest_daily"`                | `--mode BACKTEST` ou `ALL`           |
| `dq_checks`         | Todos os checks = `PASS` (exceto `WARN` para dias não úteis)             | `job_name="dq_checks"`                     | `--mode ALL` (encerra a cadeia)      |

## 5. Comunicação

- **Incidentes**: abrir ticket/slack no canal de operação com `run_id`,
  `config_version`, motivo (`reason`) e ação tomada.
- **Mudanças de configuração**: qualquer ajuste em `pipeline_config` ou
  `parametros_estrategia` deve ser feito via PR (scripts em `infra/bq/`).
- **Alertas de silêncio**: responder até 15 minutos após o disparo, registrando
  o follow-up no canal e no incidente correspondente.
