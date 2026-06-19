-- Fase 6 neural EOD — Paper trading controlado.
--
-- Complementa a camada geral de paper trading com critérios explícitos de
-- liberação para modelos neurais, execução sem capital real e monitoramento das
-- métricas exigidas no plano de sinais neurais EOD.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_paper_criteria`
(
  criteria_id STRING NOT NULL,
  criteria_version STRING NOT NULL,
  min_profit_factor FLOAT64 NOT NULL,
  min_win_rate FLOAT64 NOT NULL,
  min_fill_rate FLOAT64 NOT NULL,
  max_drawdown_pct FLOAT64 NOT NULL,
  min_trades INT64 NOT NULL,
  min_avg_return_pct FLOAT64 NOT NULL,
  max_cost_sensitivity_pct FLOAT64 NOT NULL,
  max_daily_orders INT64 NOT NULL,
  max_open_orders INT64 NOT NULL,
  default_quantity INT64 NOT NULL,
  default_cost_pct FLOAT64 NOT NULL,
  default_slippage_pct FLOAT64 NOT NULL,
  min_paper_days INT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY criteria_id, criteria_version, status
OPTIONS (
  description = "Critérios versionados para liberar modelos neurais EOD em paper trading sem capital real"
);

MERGE `ingestaokraken.cotacao_intraday.neural_eod_paper_criteria` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'neural_eod_paper_gate' AS criteria_id,
      'v1' AS criteria_version,
      1.10 AS min_profit_factor,
      0.50 AS min_win_rate,
      0.40 AS min_fill_rate,
      0.15 AS max_drawdown_pct,
      30 AS min_trades,
      0.00 AS min_avg_return_pct,
      0.25 AS max_cost_sensitivity_pct,
      5 AS max_daily_orders,
      5 AS max_open_orders,
      100 AS default_quantity,
      0.0005 AS default_cost_pct,
      0.0010 AS default_slippage_pct,
      60 AS min_paper_days,
      'active' AS status
    )
  ])
) AS source
ON target.criteria_id = source.criteria_id
  AND target.criteria_version = source.criteria_version
WHEN MATCHED THEN UPDATE SET
  min_profit_factor = source.min_profit_factor,
  min_win_rate = source.min_win_rate,
  min_fill_rate = source.min_fill_rate,
  max_drawdown_pct = source.max_drawdown_pct,
  min_trades = source.min_trades,
  min_avg_return_pct = source.min_avg_return_pct,
  max_cost_sensitivity_pct = source.max_cost_sensitivity_pct,
  max_daily_orders = source.max_daily_orders,
  max_open_orders = source.max_open_orders,
  default_quantity = source.default_quantity,
  default_cost_pct = source.default_cost_pct,
  default_slippage_pct = source.default_slippage_pct,
  min_paper_days = source.min_paper_days,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  criteria_id, criteria_version, min_profit_factor, min_win_rate, min_fill_rate,
  max_drawdown_pct, min_trades, min_avg_return_pct, max_cost_sensitivity_pct,
  max_daily_orders, max_open_orders, default_quantity, default_cost_pct,
  default_slippage_pct, min_paper_days, status, created_at, updated_at
) VALUES (
  source.criteria_id, source.criteria_version, source.min_profit_factor,
  source.min_win_rate, source.min_fill_rate, source.max_drawdown_pct,
  source.min_trades, source.min_avg_return_pct, source.max_cost_sensitivity_pct,
  source.max_daily_orders, source.max_open_orders, source.default_quantity,
  source.default_cost_pct, source.default_slippage_pct, source.min_paper_days,
  source.status, CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_paper_evaluations`
(
  evaluation_id STRING NOT NULL,
  evaluation_date DATE NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  feature_version STRING,
  criteria_id STRING NOT NULL,
  criteria_version STRING NOT NULL,
  profit_factor FLOAT64,
  win_rate FLOAT64,
  fill_rate FLOAT64,
  avg_return_pct FLOAT64,
  max_drawdown_pct FLOAT64,
  trade_count INT64,
  cost_sensitivity_pct FLOAT64,
  approved_for_paper BOOL NOT NULL,
  failed_criteria ARRAY<STRING>,
  notes STRING,
  created_at DATETIME NOT NULL
)
PARTITION BY evaluation_date
CLUSTER BY model_id, model_version, approved_for_paper
OPTIONS (
  description = "Avaliações de backtest que aprovam ou bloqueiam modelos neurais EOD antes do paper trading"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_paper_gate` AS
WITH latest_criteria AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_eod_paper_criteria`
  WHERE status = 'active'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY criteria_id ORDER BY updated_at DESC) = 1
),
latest_evaluation AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_eod_paper_evaluations`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY model_id, model_version
    ORDER BY evaluation_date DESC, created_at DESC
  ) = 1
)
SELECT
  e.*,
  c.min_paper_days,
  c.max_daily_orders,
  c.max_open_orders,
  c.default_quantity,
  c.default_cost_pct,
  c.default_slippage_pct,
  CASE
    WHEN e.approved_for_paper THEN 'liberado_paper'
    ELSE 'bloqueado_backtest'
  END AS paper_gate_status
FROM latest_evaluation AS e
JOIN latest_criteria AS c
  ON c.criteria_id = e.criteria_id
  AND c.criteria_version = e.criteria_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_paper_metrics` AS
SELECT
  strategy_version AS model_version,
  reference_date,
  COUNT(*) AS total_orders,
  COUNTIF(order_status IN ('aberta', 'entrada_simulada')) AS open_orders,
  COUNTIF(order_status IN ('encerrada', 'stop', 'target', 'expire', 'time_stop')) AS closed_orders,
  SAFE_DIVIDE(COUNTIF(simulated_entry_price IS NOT NULL), COUNT(*)) AS fill_rate,
  AVG(net_pnl_pct) AS avg_return_pct,
  SAFE_DIVIDE(
    SUM(IF(COALESCE(net_pnl_pct, 0) > 0, net_pnl_pct, 0)),
    ABS(SUM(IF(COALESCE(net_pnl_pct, 0) < 0, net_pnl_pct, 0)))
  ) AS profit_factor,
  SAFE_DIVIDE(COUNTIF(COALESCE(net_pnl_pct, 0) > 0), COUNTIF(net_pnl_pct IS NOT NULL)) AS win_rate,
  AVG(slippage_pct) AS avg_slippage_pct,
  AVG(ABS(divergence_pct)) AS avg_abs_backtest_divergence_pct
FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
WHERE strategy_family = 'neural_eod'
GROUP BY model_version, reference_date;
