-- Snapshot em SQL da estrutura atual das tabelas do BigQuery.
--
-- Uso:
-- 1) Edite project_id, dataset_id e (opcional) tables_filter.
-- 2) Rode no BigQuery: bq query --nouse_legacy_sql < infra/bq/06_schema_snapshot.sql
--
-- Se tables_filter estiver vazio ([]), o script retorna TODAS as tabelas do dataset.

DECLARE project_id STRING DEFAULT 'ingestaokraken';
DECLARE dataset_id STRING DEFAULT 'cotacao_intraday';
DECLARE tables_filter ARRAY<STRING> DEFAULT [];

DECLARE use_filter BOOL DEFAULT ARRAY_LENGTH(tables_filter) > 0;

-- Resultado 1: metadados por tabela (tipo, linhas, bytes, criação e alteração)
EXECUTE IMMEDIATE FORMAT(
  '''
  SELECT
    table_catalog AS project_id,
    table_schema AS dataset_id,
    table_name,
    table_type,
    creation_time,
    ddl
  FROM `%s.%s.INFORMATION_SCHEMA.TABLES`
  WHERE (@use_filter = FALSE OR table_name IN UNNEST(@tables_filter))
  ORDER BY table_name
  ''',
  project_id,
  dataset_id
) USING use_filter AS use_filter, tables_filter AS tables_filter;

-- Resultado 2: particionamento e clusterização
EXECUTE IMMEDIATE FORMAT(
  '''
  WITH partitioning AS (
    SELECT
      table_name,
      ANY_VALUE(partitioning_type) AS partitioning_type,
      ANY_VALUE(partitioning_field) AS partitioning_field
    FROM `%s.%s.INFORMATION_SCHEMA.PARTITIONS`
    WHERE partition_id IS NOT NULL
    GROUP BY table_name
  ),
  clustering AS (
    SELECT
      table_name,
      STRING_AGG(column_name, ', ' ORDER BY clustering_ordinal_position) AS clustering_fields
    FROM `%s.%s.INFORMATION_SCHEMA.COLUMNS`
    WHERE clustering_ordinal_position IS NOT NULL
    GROUP BY table_name
  )
  SELECT
    t.table_name,
    COALESCE(p.partitioning_type, 'NONE') AS partitioning_type,
    COALESCE(p.partitioning_field, '-') AS partitioning_field,
    COALESCE(c.clustering_fields, '-') AS clustering_fields
  FROM `%s.%s.INFORMATION_SCHEMA.TABLES` t
  LEFT JOIN partitioning p USING (table_name)
  LEFT JOIN clustering c USING (table_name)
  WHERE (@use_filter = FALSE OR t.table_name IN UNNEST(@tables_filter))
  ORDER BY t.table_name
  ''',
  project_id,
  dataset_id,
  project_id,
  dataset_id,
  project_id,
  dataset_id
) USING use_filter AS use_filter, tables_filter AS tables_filter;

-- Resultado 3: schema detalhado (colunas)
EXECUTE IMMEDIATE FORMAT(
  '''
  SELECT
    table_name,
    ordinal_position,
    column_name,
    data_type,
    is_nullable,
    is_partitioning_column,
    clustering_ordinal_position,
    collation_name,
    column_default,
    description
  FROM `%s.%s.INFORMATION_SCHEMA.COLUMNS`
  WHERE (@use_filter = FALSE OR table_name IN UNNEST(@tables_filter))
  ORDER BY table_name, ordinal_position
  ''',
  project_id,
  dataset_id
) USING use_filter AS use_filter, tables_filter AS tables_filter;

-- Resultado 4: tabelas solicitadas no filtro que não existem no dataset
EXECUTE IMMEDIATE FORMAT(
  '''
  WITH requested AS (
    SELECT table_name
    FROM UNNEST(@tables_filter) AS table_name
  ),
  available AS (
    SELECT table_name
    FROM `%s.%s.INFORMATION_SCHEMA.TABLES`
  )
  SELECT r.table_name AS missing_table
  FROM requested r
  LEFT JOIN available a USING (table_name)
  WHERE a.table_name IS NULL
  ORDER BY r.table_name
  ''',
  project_id,
  dataset_id
) USING tables_filter AS tables_filter;
