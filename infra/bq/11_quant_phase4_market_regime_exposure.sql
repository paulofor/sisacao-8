-- Fase 4 — Filtros de regime e controle de exposição.
--
-- Este script prepara a camada de classificação de regimes de mercado e
-- recomendação de exposição para os novos sistemas quantitativos. Ele reutiliza
-- features diárias da Fase 2, rankings da Fase 3 e métricas/trades da Fase 1.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_regime_policy_config`
(
  policy_id STRING NOT NULL,
  policy_version STRING NOT NULL,
  description STRING NOT NULL,
  trend_up_breadth_threshold FLOAT64 NOT NULL,
  trend_down_breadth_threshold FLOAT64 NOT NULL,
  high_volatility_quantile FLOAT64 NOT NULL,
  low_volatility_quantile FLOAT64 NOT NULL,
  stress_return_5d_threshold FLOAT64 NOT NULL,
  stress_breadth_threshold FLOAT64 NOT NULL,
  normal_exposure_pct FLOAT64 NOT NULL,
  reduced_exposure_pct FLOAT64 NOT NULL,
  cash_exposure_pct FLOAT64 NOT NULL,
  max_trades_normal INT64 NOT NULL,
  max_trades_reduced INT64 NOT NULL,
  risk_per_trade_normal_pct FLOAT64 NOT NULL,
  risk_per_trade_reduced_pct FLOAT64 NOT NULL,
  daily_loss_limit_normal_pct FLOAT64 NOT NULL,
  daily_loss_limit_reduced_pct FLOAT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY policy_id, policy_version, status
OPTIONS (
  description = "Políticas versionadas de regime de mercado e controle de exposição da Fase 4"
);

MERGE `ingestaokraken.cotacao_intraday.quant_regime_policy_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'market_regime_exposure_v1' AS policy_id,
      'v1' AS policy_version,
      'Política inicial baseada em tendência, amplitude, volatilidade realizada e stress de curto prazo.' AS description,
      0.60 AS trend_up_breadth_threshold,
      0.40 AS trend_down_breadth_threshold,
      0.75 AS high_volatility_quantile,
      0.25 AS low_volatility_quantile,
      -0.04 AS stress_return_5d_threshold,
      0.30 AS stress_breadth_threshold,
      1.00 AS normal_exposure_pct,
      0.50 AS reduced_exposure_pct,
      0.00 AS cash_exposure_pct,
      5 AS max_trades_normal,
      2 AS max_trades_reduced,
      0.010 AS risk_per_trade_normal_pct,
      0.005 AS risk_per_trade_reduced_pct,
      0.030 AS daily_loss_limit_normal_pct,
      0.015 AS daily_loss_limit_reduced_pct,
      'em_teste' AS status
    )
  ])
) AS source
ON target.policy_id = source.policy_id AND target.policy_version = source.policy_version
WHEN MATCHED THEN UPDATE SET
  description = source.description,
  trend_up_breadth_threshold = source.trend_up_breadth_threshold,
  trend_down_breadth_threshold = source.trend_down_breadth_threshold,
  high_volatility_quantile = source.high_volatility_quantile,
  low_volatility_quantile = source.low_volatility_quantile,
  stress_return_5d_threshold = source.stress_return_5d_threshold,
  stress_breadth_threshold = source.stress_breadth_threshold,
  normal_exposure_pct = source.normal_exposure_pct,
  reduced_exposure_pct = source.reduced_exposure_pct,
  cash_exposure_pct = source.cash_exposure_pct,
  max_trades_normal = source.max_trades_normal,
  max_trades_reduced = source.max_trades_reduced,
  risk_per_trade_normal_pct = source.risk_per_trade_normal_pct,
  risk_per_trade_reduced_pct = source.risk_per_trade_reduced_pct,
  daily_loss_limit_normal_pct = source.daily_loss_limit_normal_pct,
  daily_loss_limit_reduced_pct = source.daily_loss_limit_reduced_pct,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  policy_id, policy_version, description, trend_up_breadth_threshold,
  trend_down_breadth_threshold, high_volatility_quantile, low_volatility_quantile,
  stress_return_5d_threshold, stress_breadth_threshold, normal_exposure_pct,
  reduced_exposure_pct, cash_exposure_pct, max_trades_normal, max_trades_reduced,
  risk_per_trade_normal_pct, risk_per_trade_reduced_pct,
  daily_loss_limit_normal_pct, daily_loss_limit_reduced_pct, status, created_at, updated_at
) VALUES (
  source.policy_id, source.policy_version, source.description, source.trend_up_breadth_threshold,
  source.trend_down_breadth_threshold, source.high_volatility_quantile, source.low_volatility_quantile,
  source.stress_return_5d_threshold, source.stress_breadth_threshold, source.normal_exposure_pct,
  source.reduced_exposure_pct, source.cash_exposure_pct, source.max_trades_normal, source.max_trades_reduced,
  source.risk_per_trade_normal_pct, source.risk_per_trade_reduced_pct,
  source.daily_loss_limit_normal_pct, source.daily_loss_limit_reduced_pct, source.status,
  CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase4_market_regime_indicators` AS
WITH features AS (
  SELECT
    ticker,
    reference_date,
    close,
    sma_20,
    sma_50,
    volume_financeiro,
    avg_volume_20d,
    return_5d,
    return_20d,
    STDDEV_POP(SAFE_DIVIDE(close, prior_close) - 1)
      OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS volatility_20d
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_daily_features`
),
market_daily AS (
  SELECT
    reference_date,
    COUNT(*) AS eligible_tickers,
    AVG(return_5d) AS market_return_5d,
    AVG(return_20d) AS market_return_20d,
    AVG(volatility_20d) AS realized_volatility_20d,
    AVG(IF(close > sma_20, 1, 0)) AS pct_above_sma_20,
    AVG(IF(close > sma_50, 1, 0)) AS pct_above_sma_50,
    AVG(IF(return_5d > 0, 1, 0)) AS pct_positive_5d,
    SUM(volume_financeiro) AS aggregate_financial_volume,
    SAFE_DIVIDE(SUM(volume_financeiro), NULLIF(SUM(avg_volume_20d), 0)) AS aggregate_relative_volume
  FROM features
  WHERE volatility_20d IS NOT NULL
  GROUP BY reference_date
),
with_percentiles AS (
  SELECT
    *,
    PERCENT_RANK() OVER (ORDER BY realized_volatility_20d) AS volatility_percentile,
    AVG(realized_volatility_20d) OVER (ORDER BY reference_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS avg_market_volatility_60d
  FROM market_daily
)
SELECT
  reference_date,
  eligible_tickers,
  market_return_5d,
  market_return_20d,
  realized_volatility_20d,
  avg_market_volatility_60d,
  volatility_percentile,
  pct_above_sma_20,
  pct_above_sma_50,
  pct_positive_5d,
  aggregate_financial_volume,
  aggregate_relative_volume,
  CASE
    WHEN market_return_5d <= -0.04 AND pct_above_sma_20 <= 0.30 THEN 'stress'
    WHEN pct_above_sma_20 >= 0.60 AND market_return_20d > 0 THEN 'alta_tendencia'
    WHEN pct_above_sma_20 <= 0.40 AND market_return_20d < 0 THEN 'baixa_tendencia'
    WHEN volatility_percentile >= 0.75 THEN 'alta_volatilidade'
    WHEN volatility_percentile <= 0.25 THEN 'baixa_volatilidade'
    ELSE 'lateral'
  END AS market_regime,
  TO_JSON_STRING(STRUCT(
    market_return_5d,
    market_return_20d,
    realized_volatility_20d,
    volatility_percentile,
    pct_above_sma_20,
    pct_above_sma_50,
    pct_positive_5d,
    aggregate_relative_volume
  )) AS regime_indicators_json
FROM with_percentiles;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase4_exposure_recommendation` AS
WITH latest_policy AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_regime_policy_config`
  WHERE status = 'em_teste'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_id ORDER BY updated_at DESC) = 1
),
regimes AS (
  SELECT * FROM `ingestaokraken.cotacao_intraday.vw_quant_phase4_market_regime_indicators`
)
SELECT
  p.policy_id,
  p.policy_version,
  r.reference_date,
  r.market_regime,
  r.market_return_5d,
  r.market_return_20d,
  r.realized_volatility_20d,
  r.volatility_percentile,
  r.pct_above_sma_20,
  r.pct_above_sma_50,
  r.aggregate_relative_volume,
  CASE
    WHEN r.market_regime = 'stress' THEN 'ficar_em_caixa'
    WHEN r.market_regime = 'baixa_tendencia' THEN 'bloquear_compras'
    WHEN r.market_regime = 'alta_volatilidade' THEN 'reduzir_posicao'
    WHEN r.market_regime = 'alta_tendencia' THEN 'operar_normal'
    WHEN r.market_regime = 'baixa_volatilidade' THEN 'operar_normal'
    ELSE 'reduzir_posicao'
  END AS exposure_action,
  CASE
    WHEN r.market_regime = 'stress' THEN p.cash_exposure_pct
    WHEN r.market_regime IN ('baixa_tendencia', 'alta_volatilidade', 'lateral') THEN p.reduced_exposure_pct
    ELSE p.normal_exposure_pct
  END AS max_exposure_pct,
  CASE
    WHEN r.market_regime IN ('stress', 'baixa_tendencia') THEN p.max_trades_reduced
    WHEN r.market_regime IN ('alta_volatilidade', 'lateral') THEN p.max_trades_reduced
    ELSE p.max_trades_normal
  END AS max_trades,
  CASE
    WHEN r.market_regime IN ('stress', 'baixa_tendencia', 'alta_volatilidade', 'lateral') THEN p.risk_per_trade_reduced_pct
    ELSE p.risk_per_trade_normal_pct
  END AS risk_per_trade_pct,
  CASE
    WHEN r.market_regime IN ('stress', 'baixa_tendencia', 'alta_volatilidade', 'lateral') THEN p.daily_loss_limit_reduced_pct
    ELSE p.daily_loss_limit_normal_pct
  END AS daily_loss_limit_pct,
  CASE
    WHEN r.market_regime = 'stress' THEN 'Stress detectado: retorno curto negativo e baixa amplitude; recomendação é caixa.'
    WHEN r.market_regime = 'baixa_tendencia' THEN 'Tendência de baixa: bloquear compras direcionais e reduzir risco.'
    WHEN r.market_regime = 'alta_volatilidade' THEN 'Volatilidade elevada: reduzir posição e limitar quantidade de operações.'
    WHEN r.market_regime = 'alta_tendencia' THEN 'Tendência de alta com amplitude saudável: operar normal dentro dos limites.'
    WHEN r.market_regime = 'baixa_volatilidade' THEN 'Volatilidade baixa: operar normal, monitorando rompimentos falsos.'
    ELSE 'Mercado lateral: operar seletivamente com exposição reduzida.'
  END AS recommendation_reason
FROM regimes AS r
CROSS JOIN latest_policy AS p;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase4_strategy_regime_performance` AS
WITH trades AS (
  SELECT
    t.strategy_id,
    t.strategy_version,
    DATE(t.entry_timestamp) AS entry_date,
    t.net_pnl_pct,
    t.outcome
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades` AS t
),
joined AS (
  SELECT
    t.strategy_id,
    t.strategy_version,
    r.market_regime,
    t.net_pnl_pct,
    t.outcome
  FROM trades AS t
  INNER JOIN `ingestaokraken.cotacao_intraday.vw_quant_phase4_market_regime_indicators` AS r
    ON r.reference_date = t.entry_date
)
SELECT
  strategy_id,
  strategy_version,
  market_regime,
  COUNT(*) AS trades,
  AVG(net_pnl_pct) AS expectancy_net_pct,
  AVG(IF(net_pnl_pct > 0, 1, 0)) AS win_rate,
  SAFE_DIVIDE(SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)), ABS(NULLIF(SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)), 0))) AS profit_factor,
  SUM(net_pnl_pct) AS total_net_pnl_pct,
  CASE
    WHEN COUNT(*) < 30 THEN 'amostra_insuficiente'
    WHEN AVG(net_pnl_pct) > 0 THEN 'favoravel'
    ELSE 'desfavoravel'
  END AS regime_effect_status
FROM joined
GROUP BY strategy_id, strategy_version, market_regime;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase4_filter_effectiveness` AS
WITH trades AS (
  SELECT
    t.strategy_id,
    t.strategy_version,
    DATE(t.entry_timestamp) AS entry_date,
    t.net_pnl_pct
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades` AS t
),
classified AS (
  SELECT
    t.*,
    e.market_regime,
    e.exposure_action,
    e.max_exposure_pct,
    e.exposure_action IN ('operar_normal', 'reduzir_posicao') AS allowed_by_regime
  FROM trades AS t
  INNER JOIN `ingestaokraken.cotacao_intraday.vw_quant_phase4_exposure_recommendation` AS e
    ON e.reference_date = t.entry_date
)
SELECT
  strategy_id,
  strategy_version,
  COUNT(*) AS original_trades,
  COUNTIF(allowed_by_regime) AS trades_after_filter,
  AVG(net_pnl_pct) AS original_expectancy_net_pct,
  AVG(IF(allowed_by_regime, net_pnl_pct, NULL)) AS filtered_expectancy_net_pct,
  AVG(IF(NOT allowed_by_regime, net_pnl_pct, NULL)) AS blocked_expectancy_net_pct,
  SAFE_DIVIDE(COUNTIF(NOT allowed_by_regime), COUNT(*)) AS blocked_trade_pct,
  SUM(net_pnl_pct) AS original_total_net_pnl_pct,
  SUM(IF(allowed_by_regime, net_pnl_pct * max_exposure_pct, 0)) AS exposure_adjusted_total_net_pnl_pct,
  CASE
    WHEN COUNT(*) < 30 THEN 'amostra_insuficiente'
    WHEN AVG(IF(allowed_by_regime, net_pnl_pct, NULL)) > AVG(net_pnl_pct) THEN 'filtro_melhorou_expectancy'
    WHEN AVG(IF(NOT allowed_by_regime, net_pnl_pct, NULL)) < 0 THEN 'bloqueio_removeu_perdas'
    ELSE 'sem_melhoria_clara'
  END AS filter_effectiveness_status
FROM classified
GROUP BY strategy_id, strategy_version;
