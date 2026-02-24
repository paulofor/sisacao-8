-- Criação do dataset principal utilizado por todas as funções do Sisacao-8.

CREATE SCHEMA IF NOT EXISTS `ingestaokraken.cotacao_intraday`
OPTIONS (
  location = "us",
  default_table_expiration_days = NULL,
  description = "Dataset principal do pipeline Sisacao-8"
);
