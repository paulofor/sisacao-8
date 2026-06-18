-- Fase 1 — Sistema de sinais EOD com redes neurais.
--
-- Este script cria o contrato auditável para armazenar as saídas brutas do
-- modelo neural antes da camada de decisão operacional gravar sinais em
-- `sinais_eod`. A tabela deve ser usada somente para predições; sinais finais
-- continuam sendo responsabilidade do job `eod_signals`.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_predictions`
(
  reference_date DATE NOT NULL,
  valid_for DATE NOT NULL,
  ticker STRING NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  feature_version STRING NOT NULL,
  label_version STRING,
  inference_config_version STRING NOT NULL,
  prob_up FLOAT64 NOT NULL,
  prob_down FLOAT64 NOT NULL,
  prob_neutral FLOAT64 NOT NULL,
  suggested_action STRING NOT NULL,
  confidence FLOAT64 NOT NULL,
  decision_threshold FLOAT64 NOT NULL,
  close FLOAT64,
  financial_volume FLOAT64,
  feature_snapshot STRING NOT NULL,
  source_snapshot STRING NOT NULL,
  job_run_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  metadata_json JSON
)
PARTITION BY reference_date
CLUSTER BY ticker, model_id, model_version, suggested_action
OPTIONS (
  description = "Predições neurais EOD brutas por ticker/data antes da decisão operacional de sinais"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_predictions_latest` AS
SELECT *
FROM `ingestaokraken.cotacao_intraday.neural_eod_predictions`
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY reference_date, valid_for, ticker, model_id
  ORDER BY created_at DESC, job_run_id DESC
) = 1;
