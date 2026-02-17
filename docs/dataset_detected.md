# Dataset detectado

As consultas em `INFORMATION_SCHEMA` para as regiões `region-us-east1` e `region-us` identificaram o dataset `cotacao_intraday` como repositório principal das séries normalizadas utilizadas pelo Sisacao-8.

## Variáveis detectadas

```text
DATASET_NAME=cotacao_intraday
PRICE_TABLE_INTRADAY_RAW=cotacao_b3
PRICE_TABLE_INTRADAY_15M=candles_intraday_15m
PRICE_TABLE_INTRADAY_1H=candles_intraday_1h
PRICE_TABLE_DAILY=candles_diarios
COL_DATETIME=candle_datetime
COL_DATE=reference_date
COL_OPEN=open
COL_HIGH=high
COL_LOW=low
COL_CLOSE=close
COL_VOLUME=volume
COL_FLAGS=data_quality_flags
COL_SOURCE=source
COL_TIMEFRAME=timeframe
```

## Consultas utilizadas

### Listagem de tabelas do dataset

```sql
SELECT
  table_name
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.TABLES;
```

### Inspeção das colunas relevantes

```sql
-- Candles diários
SELECT column_name, data_type
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'candles_diarios'
ORDER BY ordinal_position;

-- Candles intraday de 15 minutos
SELECT column_name, data_type
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'candles_intraday_15m'
ORDER BY ordinal_position;
```

As colunas `open`, `high`, `low`, `close` e `volume` agora ficam disponíveis em todas as granularidades, permitindo calcular ATR, Bollinger Bands e métricas de risco sem workarounds. O campo `data_quality_flags` registra condições como `ZERO_VOLUME`, `SINGLE_QUOTE_BUCKET` ou `ROLLED_UP`, auxiliando filtros e monitoramento.

A nova tabela `signals_eod_v0` armazena os sinais condicionais gerados pela função `eod_signals` com schema fixo (`reference_date`, `valid_for`, `ticker`, `side`, `entry`, `target`, `stop`, `rank`, `model_version`, `source_snapshot`, `code_version`).
