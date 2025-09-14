-- Daily signals table populated from `mv_indicadores`
-- Replace `PROJECT_ID` and `dataset` with your BigQuery project and dataset names.

DECLARE run_date DATE DEFAULT DATE(CURRENT_DATE('America/Sao_Paulo'));

CREATE TABLE IF NOT EXISTS `PROJECT_ID.dataset.signals_oscilacoes` (
    dt DATE,
    ticker STRING,
    long_reversion BOOL,
    short_reversion BOOL,
    stop FLOAT64,
    alvo FLOAT64,
    close FLOAT64,
    bb_dn FLOAT64,
    bb_up FLOAT64,
    rsi14 FLOAT64,
    slope50_pct FLOAT64,
    atr14 FLOAT64
) PARTITION BY dt;

DELETE FROM `PROJECT_ID.dataset.signals_oscilacoes` WHERE dt = run_date;

INSERT INTO `PROJECT_ID.dataset.signals_oscilacoes`
SELECT
    dt,
    ticker,
    long_reversion,
    short_reversion,
    1.5 * atr14 AS stop,
    sma20 AS alvo,
    close,
    bb_dn,
    bb_up,
    rsi14,
    slope50_pct,
    atr14
FROM (
    SELECT
        ticker,
        dt,
        close,
        sma20,
        bb_dn,
        bb_up,
        rsi14,
        atr14,
        slope50_pct,
        close <= bb_dn AND rsi14 < 35 AND slope50_pct < 0.001 AS long_reversion,
        close >= bb_up AND rsi14 > 65 AND slope50_pct < 0.001 AS short_reversion
    FROM `PROJECT_ID.dataset.mv_indicadores`
    WHERE dt = run_date
)
WHERE long_reversion OR short_reversion;
