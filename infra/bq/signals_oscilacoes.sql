-- Tabela de armazenamento dos sinais gerados pela função eod_signals.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.sinais_eod`
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
  horizon_days INT64
)
PARTITION BY date_ref
CLUSTER BY ticker
OPTIONS (
  description = "Sinais condicionais Sisacao-8 sprint 2 (baseline X/Y)"
);
