-- Fase 5 — Validação estatística e robustez.
--
-- Este script prepara artefatos analíticos para separar estratégias que apenas
-- encaixaram no histórico de estratégias com estabilidade fora da amostra,
-- robustez por subperíodos, grupos de ativos, custos ampliados e comparação
-- contra aleatorização. Ele consome trades e métricas do motor comum da Fase 1.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_validation_policy_config`
(
  policy_id STRING NOT NULL,
  policy_version STRING NOT NULL,
  description STRING NOT NULL,
  train_pct FLOAT64 NOT NULL,
  validation_pct FLOAT64 NOT NULL,
  test_pct FLOAT64 NOT NULL,
  walk_forward_window_days INT64 NOT NULL,
  walk_forward_step_days INT64 NOT NULL,
  min_trades_per_split INT64 NOT NULL,
  min_trades_per_subperiod INT64 NOT NULL,
  max_oos_degradation_pct FLOAT64 NOT NULL,
  stressed_cost_multiplier FLOAT64 NOT NULL,
  stressed_slippage_multiplier FLOAT64 NOT NULL,
  robustness_min_score FLOAT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY policy_id, policy_version, status
OPTIONS (
  description = "Políticas versionadas de validação estatística, walk-forward e robustez da Fase 5"
);

MERGE `ingestaokraken.cotacao_intraday.quant_validation_policy_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'statistical_robustness_v1' AS policy_id,
      'v1' AS policy_version,
      'Política inicial 60/20/20 com walk-forward semestral, custos estressados e alertas de overfitting.' AS description,
      0.60 AS train_pct,
      0.20 AS validation_pct,
      0.20 AS test_pct,
      126 AS walk_forward_window_days,
      21 AS walk_forward_step_days,
      30 AS min_trades_per_split,
      20 AS min_trades_per_subperiod,
      0.50 AS max_oos_degradation_pct,
      2.00 AS stressed_cost_multiplier,
      2.00 AS stressed_slippage_multiplier,
      60.0 AS robustness_min_score,
      'em_teste' AS status
    )
  ])
) AS source
ON target.policy_id = source.policy_id AND target.policy_version = source.policy_version
WHEN MATCHED THEN UPDATE SET
  description = source.description,
  train_pct = source.train_pct,
  validation_pct = source.validation_pct,
  test_pct = source.test_pct,
  walk_forward_window_days = source.walk_forward_window_days,
  walk_forward_step_days = source.walk_forward_step_days,
  min_trades_per_split = source.min_trades_per_split,
  min_trades_per_subperiod = source.min_trades_per_subperiod,
  max_oos_degradation_pct = source.max_oos_degradation_pct,
  stressed_cost_multiplier = source.stressed_cost_multiplier,
  stressed_slippage_multiplier = source.stressed_slippage_multiplier,
  robustness_min_score = source.robustness_min_score,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  policy_id, policy_version, description, train_pct, validation_pct, test_pct,
  walk_forward_window_days, walk_forward_step_days, min_trades_per_split,
  min_trades_per_subperiod, max_oos_degradation_pct, stressed_cost_multiplier,
  stressed_slippage_multiplier, robustness_min_score, status, created_at, updated_at
) VALUES (
  source.policy_id, source.policy_version, source.description, source.train_pct,
  source.validation_pct, source.test_pct, source.walk_forward_window_days,
  source.walk_forward_step_days, source.min_trades_per_split,
  source.min_trades_per_subperiod, source.max_oos_degradation_pct,
  source.stressed_cost_multiplier, source.stressed_slippage_multiplier,
  source.robustness_min_score, source.status, CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_oos_splits` AS
WITH policy AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_validation_policy_config`
  WHERE status = 'em_teste'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_id ORDER BY updated_at DESC) = 1
),
trades AS (
  SELECT
    t.*,
    ROW_NUMBER() OVER (PARTITION BY strategy_id, strategy_version ORDER BY reference_date, trade_id) AS trade_seq,
    COUNT(*) OVER (PARTITION BY strategy_id, strategy_version) AS total_trades
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades` AS t
  WHERE net_pnl_pct IS NOT NULL
)
SELECT
  p.policy_id,
  p.policy_version,
  t.strategy_id,
  t.strategy_family,
  t.strategy_version,
  t.config_version,
  t.trade_id,
  t.ticker,
  t.side,
  t.reference_date,
  t.entry_timestamp,
  t.net_pnl_pct,
  t.estimated_cost_pct,
  t.slippage_pct,
  t.outcome,
  t.regime_label,
  t.trade_seq,
  t.total_trades,
  CASE
    WHEN SAFE_DIVIDE(t.trade_seq, t.total_trades) <= p.train_pct THEN 'treino'
    WHEN SAFE_DIVIDE(t.trade_seq, t.total_trades) <= p.train_pct + p.validation_pct THEN 'validacao'
    ELSE 'teste'
  END AS validation_split
FROM trades AS t
CROSS JOIN policy AS p;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_oos_summary` AS
WITH split_metrics AS (
  SELECT
    policy_id,
    policy_version,
    strategy_id,
    strategy_family,
    strategy_version,
    validation_split,
    MIN(reference_date) AS period_start,
    MAX(reference_date) AS period_end,
    COUNT(*) AS trades,
    AVG(net_pnl_pct) AS expectancy_net_pct,
    SUM(net_pnl_pct) AS total_net_pnl_pct,
    AVG(IF(net_pnl_pct > 0, 1, 0)) AS win_rate,
    SAFE_DIVIDE(SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)), ABS(NULLIF(SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)), 0))) AS profit_factor
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_oos_splits`
  GROUP BY policy_id, policy_version, strategy_id, strategy_family, strategy_version, validation_split
),
pivoted AS (
  SELECT
    policy_id,
    policy_version,
    strategy_id,
    strategy_family,
    strategy_version,
    MIN(period_start) AS period_start,
    MAX(period_end) AS period_end,
    SUM(IF(validation_split = 'treino', trades, 0)) AS train_trades,
    SUM(IF(validation_split = 'validacao', trades, 0)) AS validation_trades,
    SUM(IF(validation_split = 'teste', trades, 0)) AS test_trades,
    MAX(IF(validation_split = 'treino', expectancy_net_pct, NULL)) AS train_expectancy_net_pct,
    MAX(IF(validation_split = 'validacao', expectancy_net_pct, NULL)) AS validation_expectancy_net_pct,
    MAX(IF(validation_split = 'teste', expectancy_net_pct, NULL)) AS test_expectancy_net_pct,
    MAX(IF(validation_split = 'treino', profit_factor, NULL)) AS train_profit_factor,
    MAX(IF(validation_split = 'validacao', profit_factor, NULL)) AS validation_profit_factor,
    MAX(IF(validation_split = 'teste', profit_factor, NULL)) AS test_profit_factor
  FROM split_metrics
  GROUP BY policy_id, policy_version, strategy_id, strategy_family, strategy_version
)
SELECT
  p.*,
  SAFE_DIVIDE(p.train_expectancy_net_pct - p.validation_expectancy_net_pct, ABS(NULLIF(p.train_expectancy_net_pct, 0))) AS validation_degradation_pct,
  SAFE_DIVIDE(p.train_expectancy_net_pct - p.test_expectancy_net_pct, ABS(NULLIF(p.train_expectancy_net_pct, 0))) AS test_degradation_pct,
  CASE
    WHEN p.train_trades < cfg.min_trades_per_split OR p.validation_trades < cfg.min_trades_per_split OR p.test_trades < cfg.min_trades_per_split THEN 'amostra_insuficiente'
    WHEN p.validation_expectancy_net_pct <= 0 OR p.test_expectancy_net_pct <= 0 THEN 'falha_fora_da_amostra'
    WHEN SAFE_DIVIDE(p.train_expectancy_net_pct - p.test_expectancy_net_pct, ABS(NULLIF(p.train_expectancy_net_pct, 0))) > cfg.max_oos_degradation_pct THEN 'degradacao_excessiva'
    ELSE 'aprovado_oos'
  END AS oos_status
FROM pivoted AS p
INNER JOIN `ingestaokraken.cotacao_intraday.quant_validation_policy_config` AS cfg
  ON cfg.policy_id = p.policy_id AND cfg.policy_version = p.policy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_walk_forward` AS
WITH trades AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`
  WHERE net_pnl_pct IS NOT NULL
),
monthly AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    DATE_TRUNC(reference_date, MONTH) AS window_start,
    DATE_SUB(DATE_ADD(DATE_TRUNC(reference_date, MONTH), INTERVAL 1 MONTH), INTERVAL 1 DAY) AS window_end,
    COUNT(*) AS trades,
    AVG(net_pnl_pct) AS expectancy_net_pct,
    SUM(net_pnl_pct) AS total_net_pnl_pct,
    SAFE_DIVIDE(SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)), ABS(NULLIF(SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)), 0))) AS profit_factor,
    AVG(IF(net_pnl_pct > 0, 1, 0)) AS win_rate
  FROM trades
  GROUP BY strategy_id, strategy_family, strategy_version, window_start, window_end
)
SELECT
  m.*,
  AVG(expectancy_net_pct) OVER (PARTITION BY strategy_id, strategy_version ORDER BY window_start ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS rolling_expectancy_6m,
  COUNTIF(expectancy_net_pct > 0) OVER (PARTITION BY strategy_id, strategy_version ORDER BY window_start ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS positive_windows_6m,
  CASE
    WHEN trades < 20 THEN 'amostra_insuficiente'
    WHEN expectancy_net_pct > 0 AND profit_factor >= 1.2 THEN 'janela_favoravel'
    WHEN expectancy_net_pct > 0 THEN 'janela_positiva_fraca'
    ELSE 'janela_negativa'
  END AS walk_forward_status
FROM monthly AS m;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_subperiod_asset_group_tests` AS
WITH trades AS (
  SELECT
    t.*,
    NTILE(5) OVER (PARTITION BY strategy_id, strategy_version ORDER BY ticker) AS asset_group
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades` AS t
  WHERE net_pnl_pct IS NOT NULL
),
subperiods AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    'subperiodo_mensal' AS test_type,
    FORMAT_DATE('%Y-%m', reference_date) AS bucket_label,
    COUNT(*) AS trades,
    AVG(net_pnl_pct) AS expectancy_net_pct,
    SUM(net_pnl_pct) AS total_net_pnl_pct,
    SAFE_DIVIDE(SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)), ABS(NULLIF(SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)), 0))) AS profit_factor
  FROM trades
  GROUP BY strategy_id, strategy_family, strategy_version, bucket_label
),
asset_groups AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    'grupo_ativos_quintil' AS test_type,
    CONCAT('grupo_', CAST(asset_group AS STRING)) AS bucket_label,
    COUNT(*) AS trades,
    AVG(net_pnl_pct) AS expectancy_net_pct,
    SUM(net_pnl_pct) AS total_net_pnl_pct,
    SAFE_DIVIDE(SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)), ABS(NULLIF(SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)), 0))) AS profit_factor
  FROM trades
  GROUP BY strategy_id, strategy_family, strategy_version, bucket_label
)
SELECT * FROM subperiods
UNION ALL
SELECT * FROM asset_groups;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_cost_stress` AS
WITH policy AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_validation_policy_config`
  WHERE status = 'em_teste'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_id ORDER BY updated_at DESC) = 1
),
trades AS (
  SELECT
    t.*,
    t.gross_pnl_pct - t.estimated_cost_pct - t.slippage_pct AS normal_cost_net_pnl_pct,
    t.gross_pnl_pct - (t.estimated_cost_pct * p.stressed_cost_multiplier) - t.slippage_pct AS stressed_cost_net_pnl_pct,
    t.gross_pnl_pct - t.estimated_cost_pct - (t.slippage_pct * p.stressed_slippage_multiplier) AS stressed_slippage_net_pnl_pct,
    t.gross_pnl_pct - (t.estimated_cost_pct * p.stressed_cost_multiplier) - (t.slippage_pct * p.stressed_slippage_multiplier) AS stressed_total_net_pnl_pct
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades` AS t
  CROSS JOIN policy AS p
  WHERE t.gross_pnl_pct IS NOT NULL
)
SELECT
  strategy_id,
  strategy_family,
  strategy_version,
  COUNT(*) AS trades,
  AVG(gross_pnl_pct) AS expectancy_without_cost_pct,
  AVG(normal_cost_net_pnl_pct) AS expectancy_normal_cost_pct,
  AVG(stressed_cost_net_pnl_pct) AS expectancy_stressed_cost_pct,
  AVG(stressed_slippage_net_pnl_pct) AS expectancy_stressed_slippage_pct,
  AVG(stressed_total_net_pnl_pct) AS expectancy_stressed_total_pct,
  CASE
    WHEN COUNT(*) < 30 THEN 'amostra_insuficiente'
    WHEN AVG(stressed_total_net_pnl_pct) > 0 THEN 'robusto_a_custos'
    WHEN AVG(normal_cost_net_pnl_pct) > 0 AND AVG(stressed_total_net_pnl_pct) <= 0 THEN 'sensivel_a_custos'
    ELSE 'sem_expectativa_liquida'
  END AS cost_stress_status
FROM trades
GROUP BY strategy_id, strategy_family, strategy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_randomization_benchmark` AS
WITH trades AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    ticker,
    reference_date,
    net_pnl_pct
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`
  WHERE net_pnl_pct IS NOT NULL
),
strategy_daily AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    reference_date,
    COUNT(*) AS strategy_trades,
    AVG(net_pnl_pct) AS strategy_expectancy_net_pct
  FROM trades
  GROUP BY strategy_id, strategy_family, strategy_version, reference_date
),
random_daily AS (
  SELECT
    s.strategy_id,
    s.strategy_family,
    s.strategy_version,
    s.reference_date,
    AVG(t.net_pnl_pct) AS random_universe_expectancy_net_pct
  FROM strategy_daily AS s
  INNER JOIN trades AS t
    ON t.reference_date = s.reference_date
  GROUP BY s.strategy_id, s.strategy_family, s.strategy_version, s.reference_date
)
SELECT
  s.strategy_id,
  s.strategy_family,
  s.strategy_version,
  COUNT(*) AS compared_days,
  AVG(s.strategy_expectancy_net_pct) AS strategy_expectancy_net_pct,
  AVG(r.random_universe_expectancy_net_pct) AS random_expectancy_net_pct,
  AVG(s.strategy_expectancy_net_pct - r.random_universe_expectancy_net_pct) AS excess_expectancy_vs_random_pct,
  AVG(IF(s.strategy_expectancy_net_pct > r.random_universe_expectancy_net_pct, 1, 0)) AS pct_days_above_random,
  CASE
    WHEN COUNT(*) < 20 THEN 'amostra_insuficiente'
    WHEN AVG(s.strategy_expectancy_net_pct - r.random_universe_expectancy_net_pct) > 0 AND AVG(IF(s.strategy_expectancy_net_pct > r.random_universe_expectancy_net_pct, 1, 0)) >= 0.55 THEN 'supera_aleatorizacao'
    ELSE 'nao_supera_aleatorizacao'
  END AS randomization_status
FROM strategy_daily AS s
INNER JOIN random_daily AS r
  ON r.strategy_id = s.strategy_id
  AND r.strategy_version = s.strategy_version
  AND r.reference_date = s.reference_date
GROUP BY s.strategy_id, s.strategy_family, s.strategy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_parameter_sensitivity` AS
WITH strategy_params AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    parameters_json
  FROM `ingestaokraken.cotacao_intraday.quant_baseline_strategy_config`
),
metrics AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    trades,
    expectancy_net_pct,
    profit_factor,
    max_drawdown_pct,
    robustness_score
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_metrics`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY strategy_id, strategy_version ORDER BY metric_date DESC) = 1
)
SELECT
  p.strategy_id,
  p.strategy_family,
  p.strategy_version,
  p.parameters_json,
  JSON_VALUE(p.parameters_json, '$.lookback_return_days') AS parameter_1_value,
  COALESCE(JSON_VALUE(p.parameters_json, '$.target_pct'), JSON_VALUE(p.parameters_json, '$.top_n'), JSON_VALUE(p.parameters_json, '$.min_gap_pct')) AS parameter_2_value,
  m.trades,
  m.expectancy_net_pct,
  m.profit_factor,
  m.max_drawdown_pct,
  m.robustness_score,
  CASE
    WHEN m.trades < 30 THEN 'amostra_insuficiente'
    WHEN m.robustness_score >= 60 THEN 'parametros_estaveis'
    WHEN m.expectancy_net_pct > 0 AND m.profit_factor >= 1.2 THEN 'candidato_a_grade_parametros'
    ELSE 'parametros_fragil'
  END AS sensitivity_status
FROM strategy_params AS p
LEFT JOIN metrics AS m
  ON m.strategy_id = p.strategy_id AND m.strategy_version = p.strategy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase5_robustness_dashboard` AS
WITH oos AS (
  SELECT * FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_oos_summary`
),
wf AS (
  SELECT
    strategy_id,
    strategy_version,
    COUNT(*) AS walk_forward_windows,
    AVG(IF(walk_forward_status IN ('janela_favoravel', 'janela_positiva_fraca'), 1, 0)) AS pct_positive_walk_forward_windows,
    AVG(expectancy_net_pct) AS avg_walk_forward_expectancy_net_pct
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_walk_forward`
  GROUP BY strategy_id, strategy_version
),
costs AS (
  SELECT * FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_cost_stress`
),
rand AS (
  SELECT * FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_randomization_benchmark`
)
SELECT
  o.policy_id,
  o.policy_version,
  o.strategy_id,
  o.strategy_family,
  o.strategy_version,
  o.period_start,
  o.period_end,
  o.train_trades,
  o.validation_trades,
  o.test_trades,
  o.train_expectancy_net_pct,
  o.validation_expectancy_net_pct,
  o.test_expectancy_net_pct,
  o.validation_degradation_pct,
  o.test_degradation_pct,
  o.oos_status,
  wf.walk_forward_windows,
  wf.pct_positive_walk_forward_windows,
  wf.avg_walk_forward_expectancy_net_pct,
  costs.expectancy_without_cost_pct,
  costs.expectancy_normal_cost_pct,
  costs.expectancy_stressed_total_pct,
  costs.cost_stress_status,
  rand.excess_expectancy_vs_random_pct,
  rand.pct_days_above_random,
  rand.randomization_status,
  LEAST(100.0, GREATEST(0.0,
    IF(o.oos_status = 'aprovado_oos', 35.0, 0.0) +
    IF(COALESCE(wf.pct_positive_walk_forward_windows, 0) >= 0.60, 25.0, COALESCE(wf.pct_positive_walk_forward_windows, 0) * 25.0) +
    IF(costs.cost_stress_status = 'robusto_a_custos', 20.0, 0.0) +
    IF(rand.randomization_status = 'supera_aleatorizacao', 20.0, 0.0)
  )) AS robustness_score,
  ARRAY_TO_STRING(ARRAY(
    SELECT alert FROM UNNEST([
      IF(o.oos_status != 'aprovado_oos', 'falha_ou_degradacao_fora_da_amostra', NULL),
      IF(COALESCE(wf.pct_positive_walk_forward_windows, 0) < 0.50, 'walk_forward_instavel', NULL),
      IF(costs.cost_stress_status != 'robusto_a_custos', 'resultado_sensivel_a_custos', NULL),
      IF(rand.randomization_status != 'supera_aleatorizacao', 'nao_supera_benchmark_aleatorio', NULL)
    ]) AS alert
    WHERE alert IS NOT NULL
  ), ',') AS overfitting_alerts
FROM oos
LEFT JOIN wf
  ON wf.strategy_id = o.strategy_id AND wf.strategy_version = o.strategy_version
LEFT JOIN costs
  ON costs.strategy_id = o.strategy_id AND costs.strategy_version = o.strategy_version
LEFT JOIN rand
  ON rand.strategy_id = o.strategy_id AND rand.strategy_version = o.strategy_version;
