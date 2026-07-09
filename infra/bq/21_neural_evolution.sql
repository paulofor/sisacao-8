-- Fase 1 — Evolução determinística de redes neurais EOD.
--
-- Cria estruturas auditáveis para rodadas, candidatos e leaderboard de avaliação.
-- A promoção continua bloqueada pelos gates de shadow/paper/promoção controlada.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_evolution_runs`
(
  evolution_run_id STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  dataset_snapshot STRING NOT NULL,
  feature_version STRING NOT NULL,
  label_version STRING NOT NULL,
  strategy STRING NOT NULL,
  budget_json JSON NOT NULL,
  status STRING NOT NULL,
  summary_json JSON
)
PARTITION BY DATE(started_at)
CLUSTER BY strategy, status, dataset_snapshot
OPTIONS (
  description = "Rodadas auditáveis de evolução determinística/assistida de modelos neurais EOD"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_candidate_configs`
(
  candidate_id STRING NOT NULL,
  evolution_run_id STRING NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  candidate_source STRING NOT NULL,
  architecture_json JSON NOT NULL,
  hyperparameters_json JSON NOT NULL,
  training_request_json JSON NOT NULL,
  schema_validation_status STRING NOT NULL,
  dedupe_hash STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY evolution_run_id, candidate_source, schema_validation_status
OPTIONS (
  description = "Configurações candidatas geradas para evolução neural EOD com deduplicação por hash"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_candidate_evaluations`
(
  candidate_id STRING NOT NULL,
  model_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  metrics_json JSON NOT NULL,
  score_total FLOAT64 NOT NULL,
  score_directional_precision FLOAT64 NOT NULL,
  score_coverage FLOAT64 NOT NULL,
  score_generalization FLOAT64 NOT NULL,
  score_stability FLOAT64 NOT NULL,
  score_cost_penalty FLOAT64 NOT NULL,
  decision STRING NOT NULL,
  decision_reasons_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY decision, model_version, dataset_snapshot
OPTIONS (
  description = "Avaliações finais e leaderboard dos candidatos neurais EOD"
);


CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_ai_advisor_audits`
(
  advisor_run_id STRING NOT NULL,
  evolution_run_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  model_name STRING NOT NULL,
  prompt_json JSON NOT NULL,
  response_json JSON,
  validation_status STRING NOT NULL,
  accepted_count INT64 NOT NULL,
  rejected_count INT64 NOT NULL,
  rejection_reasons ARRAY<STRING>
)
PARTITION BY DATE(created_at)
CLUSTER BY evolution_run_id, validation_status, model_name
OPTIONS (
  description = "Auditoria das chamadas opcionais do advisor Gemini para evolução neural EOD"
);


CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_shadow_gate_decisions`
(
  decision_date DATE NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  decision_status STRING NOT NULL,
  failed_criteria ARRAY<STRING>,
  alerts ARRAY<STRING>,
  metrics JSON NOT NULL,
  requested_by STRING NOT NULL,
  notes STRING,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY decision_date
CLUSTER BY decision_status, model_id, model_version
OPTIONS (
  description = "Decisões do gate de shadow para vencedores da evolução neural EOD"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_governance_alerts`
(
  alert_id STRING NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  alert_type STRING NOT NULL,
  severity STRING NOT NULL,
  status STRING NOT NULL,
  metrics JSON NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY alert_type, severity, status
OPTIONS (
  description = "Alertas de governança neural para overfit, queda de cobertura e drift de labels"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_evolution_leaderboard` AS
WITH latest_evaluation AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_candidate_evaluations`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY created_at DESC) = 1
), latest_run AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_evolution_runs`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY evolution_run_id ORDER BY started_at DESC) = 1
)
SELECT
  evaluation.candidate_id,
  config.evolution_run_id,
  run.strategy,
  run.status AS evolution_status,
  evaluation.model_version,
  config.model_id,
  config.candidate_source,
  run.dataset_snapshot,
  run.feature_version,
  run.label_version,
  config.architecture_json,
  config.hyperparameters_json,
  evaluation.score_total,
  evaluation.score_directional_precision,
  evaluation.score_coverage,
  evaluation.score_generalization,
  evaluation.score_stability,
  evaluation.score_cost_penalty,
  evaluation.decision,
  evaluation.decision_reasons_json,
  evaluation.created_at,
  ROW_NUMBER() OVER (
    PARTITION BY config.evolution_run_id
    ORDER BY evaluation.score_total DESC, evaluation.score_directional_precision DESC
  ) AS rank_in_run
FROM latest_evaluation AS evaluation
JOIN `ingestaokraken.cotacao_intraday.neural_candidate_configs` AS config
  USING (candidate_id)
LEFT JOIN latest_run AS run
  USING (evolution_run_id);

-- MUEN v1 — tabelas normativas para trials, folds, retornos diários, famílias e gates.
CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_protocols`
(
  protocol_version STRING NOT NULL,
  hypothesis_id STRING NOT NULL,
  protocol_json JSON NOT NULL,
  status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  frozen_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY protocol_version, status
OPTIONS (
  description = "Protocolos MUEN versionados para dados, validação, custos e gates neurais EOD"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_trials`
(
  trial_id STRING NOT NULL,
  protocol_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  candidate_family_hash STRING NOT NULL,
  candidate_id STRING NOT NULL,
  fold_id STRING NOT NULL,
  seed INT64 NOT NULL,
  code_commit STRING NOT NULL,
  state STRING NOT NULL,
  idempotency_key_json JSON NOT NULL,
  training_request_json JSON NOT NULL,
  artifact_uri STRING,
  error_message STRING,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY protocol_version, dataset_snapshot, candidate_family_hash, state
OPTIONS (
  description = "Unidades idempotentes de execução MUEN no nível candidato x fold x seed"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_fold_metrics`
(
  trial_id STRING NOT NULL,
  protocol_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  candidate_family_hash STRING NOT NULL,
  fold_id STRING NOT NULL,
  seed INT64 NOT NULL,
  cost_multiplier FLOAT64 NOT NULL,
  trades INT64 NOT NULL,
  coverage FLOAT64 NOT NULL,
  expectancy_net FLOAT64 NOT NULL,
  median_net_return FLOAT64 NOT NULL,
  total_net_return FLOAT64 NOT NULL,
  profit_factor FLOAT64 NOT NULL,
  max_drawdown FLOAT64 NOT NULL,
  positive_trade_ratio FLOAT64 NOT NULL,
  delta_expectancy_vs_champion FLOAT64 NOT NULL,
  metrics_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY protocol_version, dataset_snapshot, candidate_family_hash, fold_id
OPTIONS (
  description = "Métricas econômicas líquidas por fold externo, seed e cenário de custo"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_daily_returns`
(
  protocol_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  candidate_family_hash STRING NOT NULL,
  trial_id STRING NOT NULL,
  fold_id STRING NOT NULL,
  seed INT64 NOT NULL,
  reference_date DATE NOT NULL,
  ticker STRING,
  model_net_return FLOAT64 NOT NULL,
  champion_net_return FLOAT64 NOT NULL,
  delta_net_return FLOAT64 NOT NULL,
  exposure FLOAT64 NOT NULL,
  trades INT64 NOT NULL,
  cost_multiplier FLOAT64 NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY reference_date
CLUSTER BY protocol_version, dataset_snapshot, candidate_family_hash, ticker
OPTIONS (
  description = "Retornos diários pareados para comparação contra champion e controle de múltiplos testes"
);

ALTER TABLE `ingestaokraken.cotacao_intraday.neural_daily_returns`
ADD COLUMN IF NOT EXISTS ticker STRING;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_family_evaluations`
(
  protocol_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  candidate_family_hash STRING NOT NULL,
  folds INT64 NOT NULL,
  seeds INT64 NOT NULL,
  median_delta_expectancy_vs_champion FLOAT64 NOT NULL,
  mean_delta_expectancy_vs_champion FLOAT64 NOT NULL,
  worst_fold_delta_expectancy_vs_champion FLOAT64 NOT NULL,
  positive_folds INT64 NOT NULL,
  positive_fold_ratio FLOAT64 NOT NULL,
  median_expectancy_net FLOAT64 NOT NULL,
  max_drawdown FLOAT64 NOT NULL,
  total_trades INT64 NOT NULL,
  stable_across_seeds BOOL NOT NULL,
  cost_multipliers ARRAY<FLOAT64> NOT NULL,
  metrics_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY protocol_version, dataset_snapshot, candidate_family_hash
OPTIONS (
  description = "Agregação MUEN por família de candidatos, folds, seeds e cenários de custo"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_gate_decisions`
(
  decision_id STRING NOT NULL,
  protocol_version STRING NOT NULL,
  dataset_snapshot STRING NOT NULL,
  candidate_family_hash STRING NOT NULL,
  gate_name STRING NOT NULL,
  decision_status STRING NOT NULL,
  passed BOOL NOT NULL,
  failed_criteria ARRAY<STRING>,
  metrics_json JSON NOT NULL,
  gate_engine_version STRING NOT NULL,
  decided_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(decided_at)
CLUSTER BY protocol_version, gate_name, decision_status, candidate_family_hash
OPTIONS (
  description = "Decisões auditáveis do gate engine MUEN; leaderboard ordena, gate decide"
);
