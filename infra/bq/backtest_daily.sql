-- Tabelas do backtest diário (Sprint 3)

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.backtest_trades`
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
  description = "Trades simulados pelo backtest diário Sisacao-8"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.backtest_metrics`
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
  description = "Métricas agregadas do backtest diário Sisacao-8"
);
