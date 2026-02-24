-- Views operacionais utilizadas pelo módulo Ops API.
-- Substitua os placeholders abaixo antes de executar este script:
--   ingestaokraken  → ID do projeto no GCP
--   @@OPS_DATASET@@ → dataset onde as views de operação ficarão armazenadas (ex.: monitoring, monitoring_dev)

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_pipeline_status` AS
WITH latest_runs AS (
  SELECT
    job_name,
    ARRAY_AGG(
      STRUCT(
        run_id AS runId,
        status AS runStatus,
        COALESCE(finished_at, updated_at, started_at) AS runAt
      )
      ORDER BY COALESCE(finished_at, updated_at, started_at) DESC
      LIMIT 1
    )[SAFE_OFFSET(0)] AS last_run
  FROM `ingestaokraken.@@OPS_DATASET@@.pipeline_runs`
  GROUP BY job_name
),
config AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.pipeline_config`
  QUALIFY ROW_NUMBER() OVER (ORDER BY created_at DESC) = 1
),
thresholds AS (
  SELECT
    job_name,
    CASE job_name
      WHEN 'intraday_fetch' THEN config.intraday_max_staleness_minutes
      WHEN 'signals_eod' THEN config.signals_grace_minutes
      WHEN 'backtest_daily' THEN config.backtest_grace_minutes
      WHEN 'daily_ohlcv' THEN 1440
      WHEN 'dq_checks_daily' THEN 180
      ELSE 180
    END AS silence_threshold_minutes,
    CASE job_name
      WHEN 'intraday_fetch' THEN config.intraday_latest_time
      WHEN 'signals_eod' THEN config.signals_deadline
      WHEN 'backtest_daily' THEN config.backtest_deadline
      ELSE TIME '21:00:00'
    END AS deadline_time
  FROM latest_runs
  CROSS JOIN config
)
SELECT
  job_name AS jobName,
  last_run.runAt AS lastRunAt,
  last_run.runStatus AS lastStatus,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_run.runAt, MINUTE) AS minutesSinceLastRun,
  TIMESTAMP(DATETIME(CURRENT_DATE('America/Sao_Paulo'), COALESCE(thresholds.deadline_time, TIME '21:00:00')), 'America/Sao_Paulo') AS deadlineAt,
  CASE
    WHEN last_run.runAt IS NULL THEN TRUE
    ELSE TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_run.runAt, MINUTE) > IFNULL(thresholds.silence_threshold_minutes, 180)
  END AS isSilent,
  last_run.runId AS lastRunId
FROM latest_runs
LEFT JOIN thresholds USING (job_name)
ORDER BY jobName;

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_dq_latest` AS
SELECT
  check_date AS checkDate,
  check_name AS checkName,
  status,
  details,
  TIMESTAMP(created_at, 'America/Sao_Paulo') AS createdAt
FROM `ingestaokraken.cotacao_intraday.dq_checks_daily`
WHERE check_date >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 7 DAY)
ORDER BY createdAt DESC
LIMIT 200;

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_signals_history` AS
SELECT
  date_ref AS dateRef,
  valid_for AS validFor,
  ticker,
  side,
  entry,
  target,
  stop,
  score,
  rank,
  TIMESTAMP(created_at, 'America/Sao_Paulo') AS createdAt
FROM `ingestaokraken.cotacao_intraday.sinais_eod`
WHERE date_ref >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 365 DAY)
ORDER BY dateRef DESC, rank ASC;

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_signals_next_session` AS
WITH last_day AS (
  SELECT IFNULL(MAX(data_pregao), CURRENT_DATE('America/Sao_Paulo')) AS last_trading_day
  FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
),
next_day AS (
  SELECT MIN(candidate_day) AS next_trading_day
  FROM (
    SELECT day AS candidate_day
    FROM UNNEST(
      GENERATE_DATE_ARRAY(
        (SELECT last_trading_day FROM last_day),
        DATE_ADD((SELECT last_trading_day FROM last_day), INTERVAL 10 DAY),
        INTERVAL 1 DAY
      )
    ) AS day
    LEFT JOIN `ingestaokraken.cotacao_intraday.feriados_b3` f
      ON f.data_feriado = day AND f.ativo
    WHERE day > (SELECT last_trading_day FROM last_day)
      AND EXTRACT(DAYOFWEEK FROM day) NOT IN (1, 7)
      AND f.data_feriado IS NULL
  )
)
SELECT
  s.valid_for AS validFor,
  s.ticker,
  s.side,
  s.entry,
  s.target,
  s.stop,
  s.score,
  s.rank,
  TIMESTAMP(s.created_at, 'America/Sao_Paulo') AS createdAt
FROM `ingestaokraken.cotacao_intraday.sinais_eod` AS s
WHERE s.valid_for = (SELECT next_trading_day FROM next_day)
ORDER BY s.rank ASC
LIMIT 5;

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_incidents_open` AS
SELECT
  incident_id AS incidentId,
  check_name AS checkName,
  check_date AS checkDate,
  severity,
  COALESCE(job_name, check_name, 'unknown') AS source,
  details AS summary,
  status,
  run_id AS runId,
  TIMESTAMP(created_at, 'America/Sao_Paulo') AS createdAt
FROM `ingestaokraken.cotacao_intraday.dq_incidents`
WHERE status IN ('OPEN', 'INVESTIGATING') OR resolved_at IS NULL
ORDER BY createdAt DESC
LIMIT 200;

CREATE OR REPLACE VIEW `ingestaokraken.@@OPS_DATASET@@.vw_ops_overview` AS
WITH pipeline AS (
  SELECT * FROM `ingestaokraken.@@OPS_DATASET@@.vw_ops_pipeline_status`
),
dq AS (
  SELECT * FROM `ingestaokraken.@@OPS_DATASET@@.vw_ops_dq_latest`
),
last_day AS (
  SELECT IFNULL(MAX(data_pregao), CURRENT_DATE('America/Sao_Paulo')) AS last_trading_day
  FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
),
next_day AS (
  SELECT MIN(candidate_day) AS next_trading_day
  FROM (
    SELECT day AS candidate_day
    FROM UNNEST(
      GENERATE_DATE_ARRAY(
        (SELECT last_trading_day FROM last_day),
        DATE_ADD((SELECT last_trading_day FROM last_day), INTERVAL 10 DAY),
        INTERVAL 1 DAY
      )
    ) AS day
    LEFT JOIN `ingestaokraken.cotacao_intraday.feriados_b3` f
      ON f.data_feriado = day AND f.ativo
    WHERE day > (SELECT last_trading_day FROM last_day)
      AND EXTRACT(DAYOFWEEK FROM day) NOT IN (1, 7)
      AND f.data_feriado IS NULL
  )
),
signals AS (
  SELECT
    COUNT(*) AS total_signals,
    MAX(createdAt) AS last_created_at
  FROM `ingestaokraken.@@OPS_DATASET@@.vw_ops_signals_next_session`
),
pipeline_health AS (
  SELECT
    CASE
      WHEN EXISTS (SELECT 1 FROM pipeline WHERE isSilent) THEN 'FAIL'
      WHEN EXISTS (
        SELECT 1 FROM pipeline WHERE UPPER(lastStatus) IN ('FAIL', 'ERROR', 'CRITICAL')
      ) THEN 'FAIL'
      WHEN EXISTS (
        SELECT 1 FROM pipeline WHERE UPPER(lastStatus) IN ('WARN', 'WARNING')
      ) THEN 'WARN'
      ELSE 'OK'
    END AS status
),
dq_health AS (
  SELECT
    CASE
      WHEN EXISTS (
        SELECT 1 FROM dq WHERE UPPER(status) IN ('FAIL', 'ERROR', 'CRITICAL')
      ) THEN 'FAIL'
      WHEN EXISTS (
        SELECT 1 FROM dq WHERE UPPER(status) = 'WARN'
      ) THEN 'WARN'
      ELSE 'PASS'
    END AS status
)
SELECT
  CURRENT_TIMESTAMP() AS asOf,
  (SELECT last_trading_day FROM last_day) AS lastTradingDay,
  COALESCE((SELECT next_trading_day FROM next_day), (SELECT last_trading_day FROM last_day)) AS nextTradingDay,
  (SELECT status FROM pipeline_health) AS pipelineHealth,
  (SELECT status FROM dq_health) AS dqHealth,
  IFNULL((SELECT total_signals FROM signals), 0) > 0 AS signalsReady,
  IFNULL((SELECT total_signals FROM signals), 0) AS signalsCount,
  (SELECT last_created_at FROM signals) AS lastSignalsGeneratedAt;
