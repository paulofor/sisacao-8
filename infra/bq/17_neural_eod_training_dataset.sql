-- Fase 2 — Dataset histórico supervisionado para sinais EOD neurais.
--
-- Materializa exemplos por (ticker, reference_date), com features conhecidas
-- até o fechamento de reference_date e labels calculadas apenas com candles
-- futuros para treino histórico. A tabela não é insumo operacional direto para
-- sinais; ela serve para treino, validação, teste e auditoria de artefatos.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
(
  ticker STRING NOT NULL,
  reference_date DATE NOT NULL,
  valid_for DATE NOT NULL,
  feature_version STRING NOT NULL,
  label_version STRING NOT NULL,
  dataset_split STRING,
  open FLOAT64,
  high FLOAT64,
  low FLOAT64,
  close FLOAT64,
  volume FLOAT64,
  financial_volume FLOAT64,
  return_5d FLOAT64,
  return_10d FLOAT64,
  return_20d FLOAT64,
  volatility_10d FLOAT64,
  volatility_20d FLOAT64,
  daily_range_pct FLOAT64,
  intraday_return_pct FLOAT64,
  gap_open_pct FLOAT64,
  financial_volume_z20 FLOAT64,
  volume_ratio_20d FLOAT64,
  distance_high_20d_pct FLOAT64,
  distance_low_20d_pct FLOAT64,
  distance_sma_20d_pct FLOAT64,
  has_missing_ohlcv BOOL,
  has_zero_volume BOOL,
  is_suspicious_candle BOOL,
  label_class STRING NOT NULL,
  future_return FLOAT64 NOT NULL,
  buy_net_return FLOAT64 NOT NULL,
  sell_net_return FLOAT64 NOT NULL,
  entry_filled_buy BOOL NOT NULL,
  entry_filled_sell BOOL NOT NULL,
  days_to_event_buy INT64,
  days_to_event_sell INT64,
  created_at TIMESTAMP NOT NULL,
  dataset_snapshot STRING NOT NULL,
  metadata_json JSON
)
PARTITION BY reference_date
CLUSTER BY ticker, feature_version, label_version, dataset_split
OPTIONS (
  description = "Dataset supervisionado histórico para treino/validação/teste dos sinais EOD neurais"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_training_dataset_quality` AS
SELECT
  feature_version,
  label_version,
  dataset_split,
  COUNT(*) AS rows_count,
  COUNT(DISTINCT ticker) AS tickers_count,
  MIN(reference_date) AS min_reference_date,
  MAX(reference_date) AS max_reference_date,
  COUNTIF(label_class = 'up') AS up_count,
  COUNTIF(label_class = 'down') AS down_count,
  COUNTIF(label_class = 'neutral') AS neutral_count,
  SAFE_DIVIDE(COUNTIF(label_class = 'up'), COUNT(*)) AS up_ratio,
  SAFE_DIVIDE(COUNTIF(label_class = 'down'), COUNT(*)) AS down_ratio,
  SAFE_DIVIDE(COUNTIF(label_class = 'neutral'), COUNT(*)) AS neutral_ratio,
  COUNTIF(has_missing_ohlcv) AS missing_ohlcv_count,
  COUNTIF(has_zero_volume) AS zero_volume_count,
  COUNTIF(is_suspicious_candle) AS suspicious_candle_count
FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
GROUP BY feature_version, label_version, dataset_split;
