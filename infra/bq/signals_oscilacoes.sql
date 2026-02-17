-- Tabela de armazenamento dos sinais gerados pela função eod_signals.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.signals_eod_v0`
(
  reference_date DATE NOT NULL,
  valid_for DATE NOT NULL,
  ticker STRING NOT NULL,
  side STRING NOT NULL,
  entry FLOAT64 NOT NULL,
  target FLOAT64 NOT NULL,
  stop FLOAT64 NOT NULL,
  rank INT64 NOT NULL,
  reason STRING,
  model_version STRING NOT NULL,
  created_at DATETIME NOT NULL,
  source_snapshot STRING,
  code_version STRING,
  volume FLOAT64,
  close FLOAT64
)
PARTITION BY reference_date
CLUSTER BY ticker
OPTIONS (
  description = "Sinais condicionais Sisacao-8 sprint 1 (take-profit 7%)"
);
