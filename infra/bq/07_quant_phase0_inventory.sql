-- Fase 0 — Preparação e inventário dos dados para novos sistemas quantitativos.
--
-- Este script cria views operacionais para alimentar as telas "Inventário de Dados"
-- e "Qualidade dos Dados" descritas em docs/implementacao/plano-novos-sistemas-quantitativos.md.
-- As views são somente leitura e reutilizam as tabelas canônicas do dataset cotacao_intraday.

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_data_inventory_summary` AS
WITH daily AS (
  SELECT
    COUNT(*) AS daily_candles,
    COUNT(DISTINCT ticker) AS daily_tickers,
    MIN(data_pregao) AS first_daily_date,
    MAX(data_pregao) AS last_daily_date,
    COUNTIF(
      open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
      OR open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
      OR high < low OR high < GREATEST(open, close) OR low > LEAST(open, close)
    ) AS invalid_daily_candles,
    COUNTIF(volume_financeiro IS NULL OR volume_financeiro <= 0) AS invalid_daily_volume,
    MAX(atualizado_em) AS daily_last_update
  FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
),
intraday AS (
  SELECT
    COUNT(*) AS intraday_candles,
    COUNT(DISTINCT ticker) AS intraday_tickers,
    MIN(data) AS first_intraday_date,
    MAX(data) AS last_intraday_date,
    COUNTIF(valor IS NULL OR valor <= 0) AS invalid_intraday_prices,
    MAX(data_hora_atual) AS intraday_last_update
  FROM `ingestaokraken.cotacao_intraday.cotacao_b3`
),
tickers AS (
  SELECT
    COUNT(*) AS total_tickers,
    COUNTIF(ativo) AS active_tickers
  FROM `ingestaokraken.cotacao_intraday.acao_bovespa`
)
SELECT
  tickers.active_tickers,
  tickers.total_tickers,
  daily.daily_tickers,
  intraday.intraday_tickers,
  LEAST(daily.first_daily_date, intraday.first_intraday_date) AS first_available_date,
  GREATEST(daily.last_daily_date, intraday.last_intraday_date) AS last_available_date,
  daily.daily_candles,
  intraday.intraday_candles,
  SAFE_DIVIDE(
    daily.daily_candles + intraday.intraday_candles
      - daily.invalid_daily_candles - daily.invalid_daily_volume - intraday.invalid_intraday_prices,
    daily.daily_candles + intraday.intraday_candles
  ) AS valid_data_pct,
  GREATEST(DATETIME(daily.daily_last_update), intraday.intraday_last_update) AS last_update
FROM daily
CROSS JOIN intraday
CROSS JOIN tickers;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_ticker_coverage` AS
WITH calendar AS (
  SELECT date_ref
  FROM UNNEST(GENERATE_DATE_ARRAY(
    (SELECT MIN(data_pregao) FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`),
    (SELECT MAX(data_pregao) FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`)
  )) AS date_ref
  WHERE EXTRACT(DAYOFWEEK FROM date_ref) BETWEEN 2 AND 6
    AND date_ref NOT IN (
      SELECT data_feriado
      FROM `ingestaokraken.cotacao_intraday.feriados_b3`
      WHERE ativo
    )
),
expected AS (
  SELECT COUNT(*) AS expected_days
  FROM calendar
),
daily AS (
  SELECT
    ticker,
    MIN(data_pregao) AS first_date,
    MAX(data_pregao) AS last_date,
    COUNT(DISTINCT data_pregao) AS days_with_data,
    AVG(volume_financeiro) AS avg_financial_volume,
    COUNTIF(
      open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
      OR open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
      OR high < low OR high < GREATEST(open, close) OR low > LEAST(open, close)
    ) AS invalid_price_days,
    COUNTIF(volume_financeiro IS NULL OR volume_financeiro <= 0) AS invalid_volume_days
  FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
  GROUP BY ticker
),
duplicates AS (
  SELECT ticker, COUNT(*) AS duplicate_days
  FROM (
    SELECT ticker, data_pregao
    FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
    GROUP BY ticker, data_pregao
    HAVING COUNT(*) > 1
  )
  GROUP BY ticker
)
SELECT
  d.ticker,
  t.empresa,
  t.ativo,
  d.first_date,
  d.last_date,
  d.days_with_data,
  e.expected_days,
  SAFE_DIVIDE(d.days_with_data, e.expected_days) AS coverage_pct,
  d.avg_financial_volume,
  d.invalid_price_days,
  d.invalid_volume_days,
  COALESCE(dup.duplicate_days, 0) AS duplicate_days,
  CASE
    WHEN NOT COALESCE(t.ativo, FALSE) THEN 'inativo'
    WHEN SAFE_DIVIDE(d.days_with_data, e.expected_days) >= 0.90
      AND d.avg_financial_volume >= 1000000
      AND d.invalid_price_days = 0
      AND d.invalid_volume_days = 0
      AND COALESCE(dup.duplicate_days, 0) = 0 THEN 'elegivel'
    WHEN SAFE_DIVIDE(d.days_with_data, e.expected_days) >= 0.75 THEN 'observacao'
    ELSE 'excluir'
  END AS eligibility_status
FROM daily AS d
CROSS JOIN expected AS e
LEFT JOIN `ingestaokraken.cotacao_intraday.acao_bovespa` AS t
  ON t.ticker = d.ticker
LEFT JOIN duplicates AS dup
  ON dup.ticker = d.ticker;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_data_quality_incidents` AS
SELECT
  'daily_invalid_price' AS incident_type,
  'high' AS severity,
  ticker,
  data_pregao AS incident_date,
  FORMAT('OHLC inválido: open=%T high=%T low=%T close=%T', open, high, low, close) AS recommendation
FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
  OR open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
  OR high < low OR high < GREATEST(open, close) OR low > LEAST(open, close)
UNION ALL
SELECT
  'daily_invalid_volume' AS incident_type,
  'medium' AS severity,
  ticker,
  data_pregao AS incident_date,
  FORMAT('Volume financeiro ausente ou zerado: %T', volume_financeiro) AS recommendation
FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
WHERE volume_financeiro IS NULL OR volume_financeiro <= 0
UNION ALL
SELECT
  'daily_duplicate' AS incident_type,
  'high' AS severity,
  ticker,
  data_pregao AS incident_date,
  FORMAT('Remover ou consolidar %d candles duplicados para ticker/data.', COUNT(*)) AS recommendation
FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`
GROUP BY ticker, data_pregao
HAVING COUNT(*) > 1
UNION ALL
SELECT
  'intraday_invalid_price' AS incident_type,
  'high' AS severity,
  ticker,
  data AS incident_date,
  FORMAT('Preço intraday ausente ou zerado no horário %T.', hora) AS recommendation
FROM `ingestaokraken.cotacao_intraday.cotacao_b3`
WHERE valor IS NULL OR valor <= 0;
