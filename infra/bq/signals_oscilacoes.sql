-- (a) criar tabela vazia particionada
CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.signals_oscilacoes`
(
  ticker STRING,
  dt DATE,
  signal_type STRING,
  entry FLOAT64,
  stop FLOAT64,
  target FLOAT64,
  metrics STRUCT<
    ref_bb_dn FLOAT64, ref_bb_up FLOAT64, ref_rsi14 FLOAT64, ref_atr14 FLOAT64
  >
)
PARTITION BY dt
OPTIONS (require_partition_filter = TRUE);

-- (b) rotina idempotente de carga da partição do dia
DECLARE d DATE DEFAULT CURRENT_DATE("America/Sao_Paulo");

DELETE FROM `ingestaokraken.cotacao_intraday.signals_oscilacoes` WHERE dt = d;

INSERT INTO `ingestaokraken.cotacao_intraday.signals_oscilacoes`
SELECT
  ticker, dt, 'long_reversion',
  px_close AS entry,
  px_close - 1.5 * atr14 AS stop,
  sma20 AS target,
  STRUCT(bb_dn, bb_up, rsi14, atr14)
FROM `ingestaokraken.cotacao_intraday.mv_indicadores`
WHERE dt = d AND px_close <= bb_dn AND rsi14 < 35 AND slope50_pct < 0.001;

INSERT INTO `ingestaokraken.cotacao_intraday.signals_oscilacoes`
SELECT
  ticker, dt, 'short_reversion',
  px_close AS entry,
  px_close + 1.5 * atr14 AS stop,
  sma20 AS target,
  STRUCT(bb_dn, bb_up, rsi14, atr14)
FROM `ingestaokraken.cotacao_intraday.mv_indicadores`
WHERE dt = d AND px_close >= bb_up AND rsi14 > 65 AND slope50_pct < 0.001;
