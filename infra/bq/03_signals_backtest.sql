-- Estruturas analíticas (sinais e backtest determinístico).

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.sinais_eod`
(
  date_ref DATE NOT NULL,
  valid_for DATE NOT NULL,
  ticker STRING NOT NULL,
  side STRING NOT NULL,
  entry FLOAT64 NOT NULL,
  target FLOAT64 NOT NULL,
  stop FLOAT64 NOT NULL,
  x_rule STRING NOT NULL,
  y_target_pct FLOAT64 NOT NULL,
  y_stop_pct FLOAT64 NOT NULL,
  rank INT64 NOT NULL,
  model_version STRING NOT NULL,
  created_at DATETIME NOT NULL,
  source_snapshot STRING,
  code_version STRING,
  volume FLOAT64,
  close FLOAT64,
  ranking_key STRING,
  score FLOAT64,
  horizon_days INT64,
  valid BOOLEAN,
  job_run_id STRING,
  config_version STRING
)
PARTITION BY date_ref
CLUSTER BY ticker, side
OPTIONS (
  description = "Sinais condicionais gerados no pós-fechamento"
);

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.backtest_trades`
(
  date_ref DATE NOT NULL,
  valid_for DATE NOT NULL,
  ticker STRING NOT NULL,
  side STRING NOT NULL,
  entry FLOAT64 NOT NULL,
  target FLOAT64 NOT NULL,
  stop FLOAT64 NOT NULL,
  horizon_days INT64 NOT NULL,
  model_version STRING,
  entry_hit BOOL,
  entry_fill_date DATE,
  exit_date DATE,
  exit_reason STRING,
  exit_price FLOAT64,
  return_pct FLOAT64,
  mfe_pct FLOAT64,
  mae_pct FLOAT64,
  created_at DATETIME NOT NULL
)
PARTITION BY date_ref
CLUSTER BY ticker, side
OPTIONS (
  description = "Trades simulados pelo backtest diário"
);

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.backtest_metrics`
(
  as_of_date DATE NOT NULL,
  ticker STRING,
  side STRING,
  horizon_days INT64 NOT NULL,
  signals INT64,
  fills INT64,
  win_rate FLOAT64,
  avg_return FLOAT64,
  avg_win FLOAT64,
  avg_loss FLOAT64,
  profit_factor FLOAT64,
  avg_days_in_trade FLOAT64,
  created_at DATETIME NOT NULL
)
PARTITION BY as_of_date
CLUSTER BY ticker, side
OPTIONS (
  description = "Métricas agregadas do backtest diário"
);
