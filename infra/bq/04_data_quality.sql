-- Tabelas utilizadas pela função dq_checks para persistir resultados.

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.dq_checks_daily`
(
  check_date DATE NOT NULL,
  check_name STRING NOT NULL,
  component STRING NOT NULL,
  status STRING NOT NULL,
  severity STRING NOT NULL,
  details STRING,
  job_name STRING,
  run_id STRING,
  created_at DATETIME NOT NULL
)
PARTITION BY check_date
CLUSTER BY check_name, status
OPTIONS (
  description = "Resultados diários dos data-quality checks"
);

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.dq_incidents`
(
  incident_id STRING NOT NULL,
  check_name STRING NOT NULL,
  check_date DATE NOT NULL,
  status STRING NOT NULL,
  severity STRING NOT NULL,
  details STRING,
  job_name STRING,
  run_id STRING,
  created_at DATETIME NOT NULL,
  acknowledged_by STRING,
  acknowledged_at DATETIME,
  resolved_at DATETIME
)
PARTITION BY check_date
CLUSTER BY check_name, severity
OPTIONS (
  description = "Incidentes abertos quando um check retorna FAIL"
);
