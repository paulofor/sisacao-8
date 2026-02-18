# BigQuery — Infraestrutura como código (Sprint 4)

Os arquivos deste diretório versionam toda a estrutura necessária para o dataset
`cotacao_intraday` no BigQuery. Utilize-os como "IaC leve": basta substituir o
*placeholder* `@@PROJECT_ID@@` pelo **ID do projeto** antes de executar os
scripts com `bq query --use_legacy_sql=false`.

```bash
PROJECT_ID=ingestaokraken
for file in infra/bq/0*.sql; do
  sed "s/@@PROJECT_ID@@/${PROJECT_ID}/g" "$file" \
    | bq query --nouse_legacy_sql
done
```

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| `00_datasets.sql` | Cria o dataset `cotacao_intraday` com partições ativadas. |
| `01_config_tables.sql` | Tabelas de configuração (`acao_bovespa`, parâmetros, feriados) e carga inicial de feriados 2026-2027. |
| `02_market_data.sql` | Tabelas brutas (`cotacao_b3`) e processadas (`cotacao_ohlcv_diario`, `candles_intraday_*`). |
| `03_signals_backtest.sql` | Estruturas analíticas (`sinais_eod`, `backtest_trades`, `backtest_metrics`). |
| `04_data_quality.sql` | Tabelas `dq_checks_daily` e `dq_incidents` usadas pela função `dq_checks`. |
| `05_views.sql` | Views operacionais (`vw_pipeline_status`, `mv_indicadores`). |

Os scripts podem ser reaplicados sem efeitos colaterais graças ao uso de
`CREATE TABLE IF NOT EXISTS` e `MERGE`. Documente qualquer ajuste adicional no
repositório para manter a reprodutibilidade do ambiente.
