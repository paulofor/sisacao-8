CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.mv_indicadores` AS
WITH base AS (
  SELECT
    ticker AS ticker,
    CAST(data_pregao AS DATE) AS dt,
    preco_fechamento AS px_close,
    /* se não houver high/low, estes ficarão NULL e o ATR vira NULL */
    NULL AS px_high,
    NULL AS px_low,
    LAG(preco_fechamento) OVER (PARTITION BY ticker ORDER BY data_pregao) AS px_prev
  FROM `ingestaokraken.cotacao_intraday.candles_diarios`
),
bb AS (
  SELECT
    b.*,
    AVG(px_close) OVER w20 AS sma20,
    STDDEV_SAMP(px_close) OVER w20 AS sd20,
    AVG(px_close) OVER w50 AS sma50,
    (AVG(px_close) OVER w20) + 2 * STDDEV_SAMP(px_close) OVER w20 AS bb_up,
    (AVG(px_close) OVER w20) - 2 * STDDEV_SAMP(px_close) OVER w20 AS bb_dn,
    -- RSI14 (aprox.) por ganhos/perdas em 14 janelas
    SUM(GREATEST(px_close - px_prev, 0)) OVER w14
      / NULLIF(SUM(LEAST(px_close - px_prev, 0)) OVER w14 * -1, 0) AS rs_raw,
    -- True Range (para ATR; se high/low forem NULL, este campo ficará 0/NULL)
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
