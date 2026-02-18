-- Views operacionais para monitorar o pipeline.

CREATE OR REPLACE VIEW `@@PROJECT_ID@@.cotacao_intraday.vw_pipeline_status` AS
WITH daily AS (
  SELECT
    'cotacao_ohlcv_diario' AS component,
    MAX(data_pregao) AS last_reference,
    MAX(atualizado_em) AS last_timestamp,
    COUNTIF(data_pregao = CURRENT_DATE('America/Sao_Paulo')) AS rows_today,
    CONCAT('Último pregão: ', FORMAT_DATE('%Y-%m-%d', MAX(data_pregao))) AS notes
  FROM `@@PROJECT_ID@@.cotacao_intraday.cotacao_ohlcv_diario`
),
intraday AS (
  SELECT
    'cotacao_b3' AS component,
    MAX(data) AS last_reference,
    DATETIME(MAX(data_hora_atual)) AS last_timestamp,
    COUNTIF(data = CURRENT_DATE('America/Sao_Paulo')) AS rows_today,
    CONCAT('Última hora registrada: ', CAST(MAX(hora) AS STRING)) AS notes
  FROM `@@PROJECT_ID@@.cotacao_intraday.cotacao_b3`
),
signals AS (
  SELECT
    'sinais_eod' AS component,
    MAX(date_ref) AS last_reference,
    MAX(created_at) AS last_timestamp,
    COUNTIF(date_ref = CURRENT_DATE('America/Sao_Paulo')) AS rows_today,
    CONCAT('Válidos para: ', FORMAT_DATE('%Y-%m-%d', MAX(valid_for))) AS notes
  FROM `@@PROJECT_ID@@.cotacao_intraday.sinais_eod`
),
backtest AS (
  SELECT
    'backtest_metrics' AS component,
    MAX(as_of_date) AS last_reference,
    MAX(created_at) AS last_timestamp,
    COUNTIF(as_of_date = CURRENT_DATE('America/Sao_Paulo')) AS rows_today,
    CONCAT('Entradas avaliadas: ', CAST(SUM(signals) AS STRING)) AS notes
  FROM `@@PROJECT_ID@@.cotacao_intraday.backtest_metrics`
),
dq AS (
  SELECT
    'dq_checks_daily' AS component,
    MAX(check_date) AS last_reference,
    MAX(created_at) AS last_timestamp,
    COUNTIF(status = 'FAIL' AND check_date = CURRENT_DATE('America/Sao_Paulo')) AS rows_today,
    CONCAT('Último status: ', ANY_VALUE(status)) AS notes
  FROM `@@PROJECT_ID@@.cotacao_intraday.dq_checks_daily`
)
SELECT * FROM daily
UNION ALL SELECT * FROM intraday
UNION ALL SELECT * FROM signals
UNION ALL SELECT * FROM backtest
UNION ALL SELECT * FROM dq;

CREATE OR REPLACE VIEW `@@PROJECT_ID@@.cotacao_intraday.mv_indicadores` AS
WITH base AS (
  SELECT
    ticker,
    data_pregao AS dt,
    close AS px_close,
    high AS px_high,
    low AS px_low,
    LAG(close) OVER (PARTITION BY ticker ORDER BY data_pregao) AS px_prev
  FROM `@@PROJECT_ID@@.cotacao_intraday.cotacao_ohlcv_diario`
),
bb AS (
  SELECT
    b.*,
    AVG(px_close) OVER w20 AS sma20,
    STDDEV_SAMP(px_close) OVER w20 AS sd20,
    AVG(px_close) OVER w50 AS sma50,
    (AVG(px_close) OVER w20) + 2 * STDDEV_SAMP(px_close) OVER w20 AS bb_up,
    (AVG(px_close) OVER w20) - 2 * STDDEV_SAMP(px_close) OVER w20 AS bb_dn,
    SUM(GREATEST(px_close - px_prev, 0)) OVER w14
      / NULLIF(SUM(LEAST(px_close - px_prev, 0)) OVER w14 * -1, 0) AS rs_raw,
    GREATEST(
      COALESCE(px_high - px_low, 0),
      ABS(COALESCE(px_high, px_prev) - px_prev),
      ABS(COALESCE(px_low, px_prev) - px_prev)
    ) AS tr
  FROM base AS b
  WINDOW
    w14 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 13 PRECEDING AND CURRENT ROW),
    w20 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
    w50 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 49 PRECEDING AND CURRENT ROW)
)
SELECT
  *,
  100 - (100 / (1 + rs_raw)) AS rsi14,
  AVG(tr) OVER (
    PARTITION BY ticker
    ORDER BY dt
    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
  ) AS atr14,
  SAFE_DIVIDE(
    ABS(sma50 - LAG(sma50) OVER (PARTITION BY ticker ORDER BY dt)),
    sma50
  ) AS slope50_pct
FROM bb;
