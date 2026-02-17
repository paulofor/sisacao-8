-- Criação das tabelas padronizadas de candles diários e intraday.
-- Ajuste o nome do projeto conforme necessário antes de executar.

CREATE SCHEMA IF NOT EXISTS `ingestaokraken.cotacao_intraday`;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.candles_diarios`
(
  ticker STRING NOT NULL,
  candle_datetime DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume FLOAT64,
  trades INT64,
  turnover_brl FLOAT64,
  source STRING NOT NULL,
  timeframe STRING NOT NULL,
  ingested_at DATETIME NOT NULL,
  data_quality_flags STRING,
  quantity FLOAT64,
  window_minutes INT64,
  samples INT64
)
PARTITION BY reference_date
CLUSTER BY ticker
OPTIONS (
  description = "Candles diários normalizados ingeridos pelo pipeline sisacao-8"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.candles_intraday_15m`
(
  ticker STRING NOT NULL,
  candle_datetime DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume FLOAT64,
  source STRING NOT NULL,
  timeframe STRING NOT NULL,
  ingested_at DATETIME NOT NULL,
  data_quality_flags STRING,
  window_minutes INT64,
  samples INT64
)
PARTITION BY reference_date
CLUSTER BY ticker
OPTIONS (
  description = "Candles intraday de 15 minutos gerados a partir da coleta do Google Finance"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.candles_intraday_1h`
(
  ticker STRING NOT NULL,
  candle_datetime DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume FLOAT64,
  source STRING NOT NULL,
  timeframe STRING NOT NULL,
  ingested_at DATETIME NOT NULL,
  data_quality_flags STRING,
  window_minutes INT64,
  samples INT64
)
PARTITION BY reference_date
CLUSTER BY ticker
OPTIONS (
  description = "Candles intraday de 1 hora derivados da série de 15 minutos"
);
