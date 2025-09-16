# Dataset detectado

As consultas em `INFORMATION_SCHEMA` para as regiões `region-us-east1` e `region-us` identificaram um único dataset de cotações com os campos necessários para indicadores técnicos.

## Variáveis detectadas

```text
DATASET_NAME=cotacao_intraday
PRICE_TABLE_INTRADAY=cotacao_bovespa
PRICE_TABLE_FECHAMENTO=cotacao_fechamento_diario
COL_DATE_INTRADAY=data
COL_CLOSE_INTRADAY=valor
COL_DATE_FECHAMENTO=data_pregao
COL_CLOSE_FECHAMENTO=preco_fechamento
COL_TICKER=ticker
COL_HIGH=NULL
COL_LOW=NULL
```

## Consultas utilizadas

### Listagem de datasets por região

```sql
-- region-us-east1
SELECT
  schema_name
FROM `region-us-east1`.INFORMATION_SCHEMA.SCHEMATA
WHERE catalog_name = 'ingestaokraken';

-- region-us
SELECT
  schema_name
FROM `region-us`.INFORMATION_SCHEMA.SCHEMATA
WHERE catalog_name = 'ingestaokraken';
```

### Inspeção de tabelas e colunas do dataset escolhido

```sql
-- Tabelas do dataset detectado
SELECT
  table_name
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.TABLES;

-- Colunas da tabela intraday
SELECT
  column_name,
  data_type
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'cotacao_bovespa'
ORDER BY ordinal_position;

-- Colunas da tabela de fechamento diário
SELECT
  column_name,
  data_type
FROM `ingestaokraken.cotacao_intraday`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'cotacao_fechamento_diario'
ORDER BY ordinal_position;
```

As colunas `data`, `valor` e `ticker` foram usadas para montar as métricas intraday. Para a série oficial de fechamento diário a função `get_stock_data` grava em `cotacao_fechamento_diario` utilizando os campos `data_pregao`, `preco_fechamento` e `ticker`. O dataset não possui máximas e mínimas diárias, portanto os campos opcionais `COL_HIGH` e `COL_LOW` permanecem nulos e os cálculos que dependem deles (como o ATR) retornam `NULL` ou `0`.
