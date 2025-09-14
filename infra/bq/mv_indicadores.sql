-- Materialized view of technical indicators
-- Replace `PROJECT_ID` and `dataset` with your BigQuery project and dataset names.

CREATE OR REPLACE VIEW `PROJECT_ID.dataset.mv_indicadores` AS
WITH ohlc AS (
    SELECT
        ticker,
        DATE(data) AS dt,
        valor AS close,
        -- Substitute NULLs below with actual columns `high` and `low` if available
        NULL AS high,
        NULL AS low,
        LAG(valor) OVER (PARTITION BY ticker ORDER BY data) AS prev_close
    FROM `PROJECT_ID.dataset.cotacao_bovespa`
),
deltas AS (
    SELECT
        *,
        close - LAG(close) OVER (PARTITION BY ticker ORDER BY dt) AS delta
    FROM ohlc
),
ind AS (
    SELECT
        *,
        AVG(close) OVER w20 AS sma20,
        STDDEV_SAMP(close) OVER w20 AS std20,
        AVG(close) OVER w50 AS sma50,
        SAFE_DIVIDE(
            AVG(close) OVER w50 - LAG(AVG(close) OVER w50) OVER (PARTITION BY ticker ORDER BY dt),
            LAG(AVG(close) OVER w50) OVER (PARTITION BY ticker ORDER BY dt)
        ) AS slope50_pct,
        AVG(GREATEST(delta, 0)) OVER w14 AS avg_gain,
        AVG(GREATEST(-delta, 0)) OVER w14 AS avg_loss,
        CASE
            WHEN high IS NOT NULL AND low IS NOT NULL THEN
                AVG(GREATEST(high - low, ABS(high - prev_close), ABS(low - prev_close))) OVER w14
        END AS atr14
    FROM deltas
    WINDOW
        w20 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
        w50 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 49 PRECEDING AND CURRENT ROW),
        w14 AS (PARTITION BY ticker ORDER BY dt ROWS BETWEEN 13 PRECEDING AND CURRENT ROW)
)
SELECT
    ticker,
    dt,
    close,
    sma20,
    sma20 + 2 * std20 AS bb_up,
    sma20 - 2 * std20 AS bb_dn,
    100 - 100 / (1 + avg_gain / NULLIF(avg_loss, 0)) AS rsi14,
    atr14,
    slope50_pct
FROM ind;
