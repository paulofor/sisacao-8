-- Tabelas de ingestão e consolidação de preços (intraday + diário).

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.cotacao_b3`
(
  ticker STRING NOT NULL,
  data DATE NOT NULL,
  hora TIME NOT NULL,
  valor FLOAT64 NOT NULL,
  hora_atual TIME,
  data_hora_atual DATETIME,
  ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  fonte STRING,
  job_run_id STRING
)
PARTITION BY data
CLUSTER BY ticker
OPTIONS (
  description = "Coletas intraday vindas do Google Finance"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
(
  ticker STRING NOT NULL,
  data_pregao DATE NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume_financeiro FLOAT64,
  qtd_negociada FLOAT64,
  num_negocios INT64,
  fonte STRING NOT NULL,
  atualizado_em DATETIME NOT NULL,
  data_quality_flags STRING,
  fator_cotacao INT64,
  ingestion_run_id STRING
)
PARTITION BY data_pregao
CLUSTER BY ticker
OPTIONS (
  description = "Candles diários ingeridos via arquivo oficial da B3"
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
  description = "Candles intraday agregados em janelas de 15 minutos"
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
  description = "Candles agregados em 1 hora a partir da série de 15m"
);
