-- Criação dos datasets principais utilizados pelo Sisacao-8.
-- Ambos precisam estar na mesma location para permitir queries/views entre datasets.

CREATE SCHEMA IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday`
OPTIONS (
  location = "us-east1",
  default_table_expiration_days = NULL,
  description = "Dataset principal do pipeline Sisacao-8"
);

CREATE SCHEMA IF NOT EXISTS `@@PROJECT_ID@@.monitoring`
OPTIONS (
  location = "us-east1",
  default_table_expiration_days = NULL,
  description = "Dataset de monitoramento e views da Ops API"
);
