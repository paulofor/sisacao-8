-- Fase 3 — Registro de modelos neurais EOD baseline.
--
-- Mantém metadados imutáveis do artefato treinado, métricas por split e
-- compatibilidade de features/labels para bloquear inferência com contrato
-- divergente. A tabela não promove modelos automaticamente; o status inicial
-- deve ser "candidate" até validação em shadow/paper trading.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_model_registry`
(
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  status STRING NOT NULL,
  feature_version STRING NOT NULL,
  label_version STRING NOT NULL,
  training_dataset_snapshot STRING NOT NULL,
  artifact_uri STRING NOT NULL,
  feature_columns ARRAY<STRING> NOT NULL,
  label_classes ARRAY<STRING> NOT NULL,
  hyperparameters_json JSON NOT NULL,
  metrics_json JSON NOT NULL,
  confusion_matrix_json JSON,
  directional_precision FLOAT64,
  coverage FLOAT64,
  validation_accuracy FLOAT64,
  test_accuracy FLOAT64,
  trained_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  notes STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY model_id, model_version, status
OPTIONS (
  description = "Registro auditável dos modelos neurais EOD treinados e suas métricas de baseline"
);
