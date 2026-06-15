-- Fase 3 — Ranking e seleção de ativos para novos sistemas quantitativos.
--
-- Este script prepara a camada de ranking relativo descrita no plano quantitativo.
-- Ele reutiliza o universo elegível da Fase 0, as features diárias da Fase 2 e
-- o contrato comum da Fase 1 para produzir rankings, carteiras top N e métricas
-- de monotonicidade por decil.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_ranking_model_config`
(
  ranking_model_id STRING NOT NULL,
  ranking_model_version STRING NOT NULL,
  description STRING NOT NULL,
  rebalance_frequency STRING NOT NULL,
  holding_period_days INT64 NOT NULL,
  top_n_values ARRAY<INT64> NOT NULL,
  relative_strength_weight FLOAT64 NOT NULL,
  short_momentum_weight FLOAT64 NOT NULL,
  relative_volume_weight FLOAT64 NOT NULL,
  volatility_weight FLOAT64 NOT NULL,
  mean_distance_weight FLOAT64 NOT NULL,
  candle_quality_weight FLOAT64 NOT NULL,
  index_regime_weight FLOAT64 NOT NULL,
  min_financial_volume FLOAT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY ranking_model_id, ranking_model_version, status
OPTIONS (
  description = "Configuração versionada dos modelos de ranking e seleção de ativos da Fase 3"
);

MERGE `ingestaokraken.cotacao_intraday.quant_ranking_model_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'asset_ranking_simple_v1' AS ranking_model_id,
      'v1' AS ranking_model_version,
      'Ranking simples por força relativa e momentum curto, com penalização leve por baixa liquidez.' AS description,
      'daily' AS rebalance_frequency,
      5 AS holding_period_days,
      [3, 5, 10] AS top_n_values,
      0.45 AS relative_strength_weight,
      0.35 AS short_momentum_weight,
      0.10 AS relative_volume_weight,
      0.00 AS volatility_weight,
      0.00 AS mean_distance_weight,
      0.10 AS candle_quality_weight,
      0.00 AS index_regime_weight,
      1000000.0 AS min_financial_volume,
      'em_teste' AS status
    ),
    STRUCT(
      'asset_ranking_weighted_v1',
      'v1',
      'Ranking ponderado por força relativa, momentum curto, volume relativo, volatilidade controlada, distância da média, qualidade do candle e regime do índice.',
      'daily',
      5,
      [3, 5, 10],
      0.30,
      0.20,
      0.15,
      0.10,
      0.10,
      0.10,
      0.05,
      1000000.0,
      'em_teste'
    )
  ])
) AS source
ON target.ranking_model_id = source.ranking_model_id
  AND target.ranking_model_version = source.ranking_model_version
WHEN MATCHED THEN UPDATE SET
  description = source.description,
  rebalance_frequency = source.rebalance_frequency,
  holding_period_days = source.holding_period_days,
  top_n_values = source.top_n_values,
  relative_strength_weight = source.relative_strength_weight,
  short_momentum_weight = source.short_momentum_weight,
  relative_volume_weight = source.relative_volume_weight,
  volatility_weight = source.volatility_weight,
  mean_distance_weight = source.mean_distance_weight,
  candle_quality_weight = source.candle_quality_weight,
  index_regime_weight = source.index_regime_weight,
  min_financial_volume = source.min_financial_volume,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  ranking_model_id, ranking_model_version, description, rebalance_frequency,
  holding_period_days, top_n_values, relative_strength_weight, short_momentum_weight,
  relative_volume_weight, volatility_weight, mean_distance_weight,
  candle_quality_weight, index_regime_weight, min_financial_volume, status,
  created_at, updated_at
) VALUES (
  source.ranking_model_id, source.ranking_model_version, source.description,
  source.rebalance_frequency, source.holding_period_days, source.top_n_values,
  source.relative_strength_weight, source.short_momentum_weight,
  source.relative_volume_weight, source.volatility_weight, source.mean_distance_weight,
  source.candle_quality_weight, source.index_regime_weight, source.min_financial_volume,
  source.status, CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase3_ranking_factors` AS
WITH features AS (
  SELECT
    f.*,
    STDDEV_POP(SAFE_DIVIDE(f.close, f.prior_close) - 1)
      OVER (PARTITION BY f.ticker ORDER BY f.reference_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS volatility_20d,
    SAFE_DIVIDE(f.close, f.sma_20) - 1 AS distance_from_sma_20,
    SAFE_DIVIDE(f.close - f.low, NULLIF(f.high - f.low, 0)) AS close_location_value,
    LEAD(f.close, 5) OVER (PARTITION BY f.ticker ORDER BY f.reference_date) AS close_5d_forward
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_daily_features` AS f
),
market AS (
  SELECT
    reference_date,
    AVG(IF(close > sma_20, 1, 0)) AS breadth_above_sma_20,
    AVG(return_5d) AS market_return_5d,
    AVG(volatility_20d) AS market_volatility_20d
  FROM features
  GROUP BY reference_date
),
ranked AS (
  SELECT
    f.*,
    m.breadth_above_sma_20,
    m.market_return_5d,
    m.market_volatility_20d,
    PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY f.return_20d) AS relative_strength_factor,
    PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY f.return_5d) AS short_momentum_factor,
    PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY f.relative_volume_20d) AS relative_volume_factor,
    1 - PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY f.volatility_20d) AS volatility_factor,
    1 - PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY ABS(f.distance_from_sma_20)) AS mean_distance_factor,
    PERCENT_RANK() OVER (PARTITION BY f.reference_date ORDER BY f.close_location_value) AS candle_quality_factor,
    IF(m.breadth_above_sma_20 >= 0.55 AND m.market_return_5d > 0, 1.0, 0.0) AS index_regime_factor,
    SAFE_DIVIDE(f.close_5d_forward, f.close) - 1 AS forward_return_5d
  FROM features AS f
  INNER JOIN market AS m ON m.reference_date = f.reference_date
  WHERE f.volume_financeiro >= 1000000
)
SELECT
  ticker,
  reference_date,
  open,
  high,
  low,
  close,
  volume_financeiro,
  avg_volume_20d,
  relative_volume_20d,
  return_5d,
  return_20d,
  volatility_20d,
  distance_from_sma_20,
  close_location_value,
  breadth_above_sma_20,
  market_return_5d,
  market_volatility_20d,
  relative_strength_factor,
  short_momentum_factor,
  relative_volume_factor,
  volatility_factor,
  mean_distance_factor,
  candle_quality_factor,
  index_regime_factor,
  forward_return_5d,
  CASE
    WHEN breadth_above_sma_20 >= 0.60 AND market_return_5d > 0 THEN 'favoravel'
    WHEN breadth_above_sma_20 <= 0.40 OR market_return_5d < -0.03 THEN 'desfavoravel'
    ELSE 'neutro'
  END AS market_regime_label
FROM ranked;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase3_daily_asset_ranking` AS
WITH scored AS (
  SELECT
    c.ranking_model_id,
    c.ranking_model_version,
    f.*,
    c.relative_strength_weight * f.relative_strength_factor
      + c.short_momentum_weight * f.short_momentum_factor
      + c.relative_volume_weight * f.relative_volume_factor
      + c.volatility_weight * f.volatility_factor
      + c.mean_distance_weight * f.mean_distance_factor
      + c.candle_quality_weight * f.candle_quality_factor
      + c.index_regime_weight * f.index_regime_factor AS final_score
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_ranking_factors` AS f
  CROSS JOIN `ingestaokraken.cotacao_intraday.quant_ranking_model_config` AS c
  WHERE c.status = 'em_teste'
    AND f.volume_financeiro >= c.min_financial_volume
),
positioned AS (
  SELECT
    ranking_model_id,
    ranking_model_version,
    reference_date,
    ROW_NUMBER() OVER (
      PARTITION BY ranking_model_id, ranking_model_version, reference_date
      ORDER BY final_score DESC, volume_financeiro DESC, ticker
    ) AS ranking_position,
    NTILE(10) OVER (
      PARTITION BY ranking_model_id, ranking_model_version, reference_date
      ORDER BY final_score DESC, volume_financeiro DESC, ticker
    ) AS ranking_decile,
    ticker,
    final_score,
    relative_strength_factor,
    short_momentum_factor,
    relative_volume_factor,
    volatility_factor,
    mean_distance_factor,
    candle_quality_factor,
    index_regime_factor,
    close AS current_price,
    volume_financeiro AS liquidity_value,
    volatility_20d AS estimated_risk,
    market_regime_label,
    forward_return_5d,
    return_5d,
    return_20d,
    relative_volume_20d,
    distance_from_sma_20,
    close_location_value
  FROM scored
)
SELECT
  ranking_model_id,
  ranking_model_version,
  reference_date,
  ranking_position,
  ranking_decile,
  ticker,
  final_score,
  relative_strength_factor,
  short_momentum_factor,
  relative_volume_factor,
  volatility_factor,
  mean_distance_factor,
  candle_quality_factor,
  index_regime_factor,
  current_price,
  liquidity_value,
  estimated_risk,
  market_regime_label,
  forward_return_5d,
  TO_JSON_STRING(STRUCT(
    relative_strength_factor,
    short_momentum_factor,
    relative_volume_factor,
    volatility_factor,
    mean_distance_factor,
    candle_quality_factor,
    index_regime_factor,
    return_5d,
    return_20d,
    relative_volume_20d,
    distance_from_sma_20,
    close_location_value
  )) AS factor_breakdown_json,
  CASE
    WHEN market_regime_label = 'desfavoravel' THEN 'evitar'
    WHEN final_score >= 0.70 AND estimated_risk <= 0.05 THEN 'operar'
    WHEN final_score >= 0.55 THEN 'observar'
    ELSE 'evitar'
  END AS action_suggestion,
  CASE
    WHEN final_score >= 0.75 AND ranking_position <= 5 THEN 'alta'
    WHEN final_score >= 0.60 AND ranking_position <= 10 THEN 'media'
    ELSE 'baixa'
  END AS confidence_label
FROM positioned;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase3_top_n_portfolios` AS
SELECT
  ranking_model_id,
  ranking_model_version,
  reference_date,
  top_n,
  COUNT(*) AS selected_assets,
  AVG(final_score) AS avg_score,
  AVG(forward_return_5d) AS avg_forward_return_5d,
  AVG(estimated_risk) AS avg_estimated_risk,
  ARRAY_AGG(ticker ORDER BY ranking_position LIMIT 10) AS selected_tickers
FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_daily_asset_ranking`
CROSS JOIN UNNEST([3, 5, 10]) AS top_n
WHERE ranking_position <= top_n
GROUP BY ranking_model_id, ranking_model_version, reference_date, top_n;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase3_ranking_performance` AS
WITH deciles AS (
  SELECT
    ranking_model_id,
    ranking_model_version,
    reference_date,
    ranking_decile,
    COUNT(*) AS assets,
    AVG(final_score) AS avg_score,
    AVG(forward_return_5d) AS avg_forward_return_5d
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_daily_asset_ranking`
  WHERE forward_return_5d IS NOT NULL
  GROUP BY ranking_model_id, ranking_model_version, reference_date, ranking_decile
),
top_n AS (
  SELECT
    ranking_model_id,
    ranking_model_version,
    top_n,
    COUNT(*) AS portfolio_days,
    AVG(avg_forward_return_5d) AS avg_top_n_return_5d,
    STDDEV_POP(avg_forward_return_5d) AS volatility_top_n_return_5d,
    COUNTIF(avg_forward_return_5d > 0) AS positive_days
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_top_n_portfolios`
  WHERE avg_forward_return_5d IS NOT NULL
  GROUP BY ranking_model_id, ranking_model_version, top_n
),
random_baseline AS (
  SELECT
    reference_date,
    AVG(forward_return_5d) AS avg_random_return_5d
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_daily_asset_ranking`
  WHERE forward_return_5d IS NOT NULL
  GROUP BY reference_date
),
top_n_with_random AS (
  SELECT
    p.ranking_model_id,
    p.ranking_model_version,
    p.top_n,
    AVG(p.avg_forward_return_5d - r.avg_random_return_5d) AS avg_excess_vs_random_5d
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase3_top_n_portfolios` AS p
  INNER JOIN random_baseline AS r ON r.reference_date = p.reference_date
  WHERE p.avg_forward_return_5d IS NOT NULL
  GROUP BY p.ranking_model_id, p.ranking_model_version, p.top_n
),
monotonicity AS (
  SELECT
    ranking_model_id,
    ranking_model_version,
    CORR(11 - ranking_decile, avg_forward_return_5d) AS decile_return_correlation,
    AVG(IF(ranking_decile = 1, avg_forward_return_5d, NULL)) AS top_decile_return_5d,
    AVG(IF(ranking_decile = 10, avg_forward_return_5d, NULL)) AS bottom_decile_return_5d
  FROM deciles
  GROUP BY ranking_model_id, ranking_model_version
)
SELECT
  t.ranking_model_id,
  t.ranking_model_version,
  t.top_n,
  t.portfolio_days,
  t.avg_top_n_return_5d,
  t.volatility_top_n_return_5d,
  SAFE_DIVIDE(t.positive_days, t.portfolio_days) AS positive_day_rate,
  r.avg_excess_vs_random_5d,
  m.decile_return_correlation,
  m.top_decile_return_5d,
  m.bottom_decile_return_5d,
  m.top_decile_return_5d - m.bottom_decile_return_5d AS top_minus_bottom_decile_return_5d,
  CASE
    WHEN t.portfolio_days < 60 THEN 'amostra_insuficiente'
    WHEN m.decile_return_correlation > 0.25 AND r.avg_excess_vs_random_5d > 0 THEN 'monotonicidade_promissora'
    WHEN m.decile_return_correlation <= 0 THEN 'sem_monotonicidade'
    ELSE 'em_observacao'
  END AS ranking_status
FROM top_n AS t
LEFT JOIN top_n_with_random AS r
  ON r.ranking_model_id = t.ranking_model_id
  AND r.ranking_model_version = t.ranking_model_version
  AND r.top_n = t.top_n
LEFT JOIN monotonicity AS m
  ON m.ranking_model_id = t.ranking_model_id
  AND m.ranking_model_version = t.ranking_model_version;
