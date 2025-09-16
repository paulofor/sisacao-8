-- Criação da tabela dedicada às cotações oficiais de fechamento diário.
-- Ajuste o nome do projeto conforme necessário antes de executar.

CREATE SCHEMA IF NOT EXISTS `ingestaokraken.cotacao_intraday`;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.cotacao_fechamento_diario`
(
  ticker STRING NOT NULL,
  data_pregao DATE NOT NULL,
  preco_fechamento FLOAT64 NOT NULL,
  data_captura DATETIME NOT NULL,
  fonte STRING NOT NULL
)
PARTITION BY data_pregao
CLUSTER BY ticker
OPTIONS (
  description = "Cotações de fechamento diário da B3 ingeridas pelo pipeline sisacao-8"
);
