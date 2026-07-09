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
  log_return_1d FLOAT64,
  log_return_5d FLOAT64,
  log_return_10d FLOAT64,
  log_return_20d FLOAT64,
  log_financial_volume FLOAT64,
  log_volume FLOAT64,
  return_1d FLOAT64,
  return_5d FLOAT64,
  return_10d FLOAT64,
  return_20d FLOAT64,
  volatility_5d FLOAT64,
  volatility_10d FLOAT64,
  volatility_20d FLOAT64,
  volatility_60d FLOAT64,
  downside_volatility_20d FLOAT64,
  daily_range_pct FLOAT64,
  intraday_return_pct FLOAT64,
  gap_open_pct FLOAT64,
  financial_volume_z20 FLOAT64,
  volume_ratio_5d FLOAT64,
  volume_ratio_20d FLOAT64,
  financial_volume_ratio_20d FLOAT64,
  trend_sma_5_20_pct FLOAT64,
  distance_high_20d_pct FLOAT64,
  distance_low_20d_pct FLOAT64,
  distance_high_60d_pct FLOAT64,
  distance_low_60d_pct FLOAT64,
  distance_sma_20d_pct FLOAT64,
  distance_sma_50d_pct FLOAT64,
  range_volatility_20d FLOAT64,
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
  trade_side STRING,
  entry_filled BOOL,
  entry_date DATE,
  entry_price FLOAT64,
  exit_date DATE,
  exit_price FLOAT64,
  exit_reason STRING,
  gross_return FLOAT64,
  net_return FLOAT64,
  holding_sessions INT64,
  max_adverse_excursion FLOAT64,
  max_favorable_excursion FLOAT64,
  execution_policy_version STRING,
  champion_strategy_id STRING,
  champion_strategy_version STRING,
  champion_signal_side STRING,
  champion_net_return FLOAT64,
  champion_trade_active BOOL,
  created_at TIMESTAMP NOT NULL,
  dataset_snapshot STRING NOT NULL,
  metadata_json JSON,
  temporal_protocol_json JSON
)
PARTITION BY reference_date
CLUSTER BY ticker, feature_version, label_version, dataset_split
OPTIONS (
  description = "Dataset supervisionado histórico para treino/validação/teste dos sinais EOD neurais"
);



-- Migração idempotente para ambientes criados antes dos contratos v2/v3 de features.
-- `CREATE TABLE IF NOT EXISTS` não altera tabelas já existentes, portanto as
-- colunas versionadas precisam ser adicionadas explicitamente antes de cargas novas.
ALTER TABLE `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
ADD COLUMN IF NOT EXISTS log_return_1d FLOAT64,
ADD COLUMN IF NOT EXISTS log_return_5d FLOAT64,
ADD COLUMN IF NOT EXISTS log_return_10d FLOAT64,
ADD COLUMN IF NOT EXISTS log_return_20d FLOAT64,
ADD COLUMN IF NOT EXISTS log_financial_volume FLOAT64,
ADD COLUMN IF NOT EXISTS log_volume FLOAT64,
ADD COLUMN IF NOT EXISTS return_1d FLOAT64,
ADD COLUMN IF NOT EXISTS volatility_5d FLOAT64,
ADD COLUMN IF NOT EXISTS volatility_60d FLOAT64,
ADD COLUMN IF NOT EXISTS downside_volatility_20d FLOAT64,
ADD COLUMN IF NOT EXISTS volume_ratio_5d FLOAT64,
ADD COLUMN IF NOT EXISTS financial_volume_ratio_20d FLOAT64,
ADD COLUMN IF NOT EXISTS trend_sma_5_20_pct FLOAT64,
ADD COLUMN IF NOT EXISTS distance_high_60d_pct FLOAT64,
ADD COLUMN IF NOT EXISTS distance_low_60d_pct FLOAT64,
ADD COLUMN IF NOT EXISTS distance_sma_50d_pct FLOAT64,
ADD COLUMN IF NOT EXISTS range_volatility_20d FLOAT64,
ADD COLUMN IF NOT EXISTS trade_side STRING,
ADD COLUMN IF NOT EXISTS entry_filled BOOL,
ADD COLUMN IF NOT EXISTS entry_date DATE,
ADD COLUMN IF NOT EXISTS entry_price FLOAT64,
ADD COLUMN IF NOT EXISTS exit_date DATE,
ADD COLUMN IF NOT EXISTS exit_price FLOAT64,
ADD COLUMN IF NOT EXISTS exit_reason STRING,
ADD COLUMN IF NOT EXISTS gross_return FLOAT64,
ADD COLUMN IF NOT EXISTS net_return FLOAT64,
ADD COLUMN IF NOT EXISTS holding_sessions INT64,
ADD COLUMN IF NOT EXISTS max_adverse_excursion FLOAT64,
ADD COLUMN IF NOT EXISTS max_favorable_excursion FLOAT64,
ADD COLUMN IF NOT EXISTS execution_policy_version STRING,
ADD COLUMN IF NOT EXISTS champion_strategy_id STRING,
ADD COLUMN IF NOT EXISTS champion_strategy_version STRING,
ADD COLUMN IF NOT EXISTS champion_signal_side STRING,
ADD COLUMN IF NOT EXISTS champion_net_return FLOAT64,
ADD COLUMN IF NOT EXISTS champion_trade_active BOOL,
ADD COLUMN IF NOT EXISTS temporal_protocol_json JSON;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_dataset_manifests`
(
  dataset_snapshot STRING NOT NULL,
  protocol_version STRING NOT NULL,
  feature_version STRING NOT NULL,
  label_version STRING NOT NULL,
  universe_version STRING NOT NULL,
  start_date DATE,
  end_date DATE,
  `rows` INT64,
  tickers INT64,
  query_hash STRING,
  code_hash STRING,
  manifest_json JSON,
  created_at TIMESTAMP NOT NULL
)
CLUSTER BY protocol_version, feature_version, label_version
OPTIONS (
  description = "Manifestos auditáveis dos snapshots point-in-time do dataset neural EOD"
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
  COUNTIF(is_suspicious_candle) AS suspicious_candle_count,
  COUNTIF(buy_net_return >= 0.07 OR sell_net_return >= 0.07) AS target_hit_count,
  COUNTIF(buy_net_return <= -0.07 OR sell_net_return <= -0.07) AS stop_hit_count
FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
GROUP BY feature_version, label_version, dataset_split;
