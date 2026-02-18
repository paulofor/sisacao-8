-- Criação das tabelas padronizadas de candles diários e intraday.
-- Ajuste o nome do projeto conforme necessário antes de executar.

CREATE SCHEMA IF NOT EXISTS `ingestaokraken.cotacao_intraday`;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
(
  ticker STRING NOT NULL,
  data_pregao DATE NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume FLOAT64,
  qtd_negociada FLOAT64,
  num_negocios INT64,
  fonte STRING NOT NULL,
  atualizado_em DATETIME NOT NULL,
  data_quality_flags STRING,
  fator_cotacao INT64
)
PARTITION BY data_pregao
CLUSTER BY ticker
OPTIONS (
  description = "Candles diários OHLCV ingeridos a partir do COTAHIST (Sisacao-8)"
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
