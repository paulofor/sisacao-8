-- Fase 6 — Simulação operacional em paper trading.
--
-- Este script prepara a camada operacional para acompanhar sinais em tempo quase
-- real sem capital real, registrando decisões, ordens simuladas, eventos do dia
-- e aderência entre preço esperado, execução simulada e resultado de backtest.
-- Ele consome os sinais canônicos da Fase 1 e as recomendações de regime da Fase 4.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_paper_trading_config`
(
  config_id STRING NOT NULL,
  config_version STRING NOT NULL,
  description STRING NOT NULL,
  default_capital_brl NUMERIC NOT NULL,
  max_daily_orders INT64 NOT NULL,
  max_open_orders INT64 NOT NULL,
  max_position_notional_brl NUMERIC NOT NULL,
  default_quantity INT64 NOT NULL,
  default_cost_pct FLOAT64 NOT NULL,
  default_slippage_pct FLOAT64 NOT NULL,
  min_paper_days INT64 NOT NULL,
  max_backtest_divergence_pct FLOAT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY config_id, config_version, status
OPTIONS (
  description = "Configurações versionadas da simulação operacional em paper trading da Fase 6"
);

MERGE `ingestaokraken.cotacao_intraday.quant_paper_trading_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'paper_trading_v1' AS config_id,
      'v1' AS config_version,
      'Configuração inicial para simulação sem capital real, com controles simples de quantidade, custos e divergência contra backtest.' AS description,
      NUMERIC '100000.00' AS default_capital_brl,
      10 AS max_daily_orders,
      5 AS max_open_orders,
      NUMERIC '20000.00' AS max_position_notional_brl,
      100 AS default_quantity,
      0.0005 AS default_cost_pct,
      0.0010 AS default_slippage_pct,
      30 AS min_paper_days,
      0.50 AS max_backtest_divergence_pct,
      'em_teste' AS status
    )
  ])
) AS source
ON target.config_id = source.config_id AND target.config_version = source.config_version
WHEN MATCHED THEN UPDATE SET
  description = source.description,
  default_capital_brl = source.default_capital_brl,
  max_daily_orders = source.max_daily_orders,
  max_open_orders = source.max_open_orders,
  max_position_notional_brl = source.max_position_notional_brl,
  default_quantity = source.default_quantity,
  default_cost_pct = source.default_cost_pct,
  default_slippage_pct = source.default_slippage_pct,
  min_paper_days = source.min_paper_days,
  max_backtest_divergence_pct = source.max_backtest_divergence_pct,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  config_id, config_version, description, default_capital_brl, max_daily_orders,
  max_open_orders, max_position_notional_brl, default_quantity, default_cost_pct,
  default_slippage_pct, min_paper_days, max_backtest_divergence_pct, status,
  created_at, updated_at
) VALUES (
  source.config_id, source.config_version, source.description, source.default_capital_brl,
  source.max_daily_orders, source.max_open_orders, source.max_position_notional_brl,
  source.default_quantity, source.default_cost_pct, source.default_slippage_pct,
  source.min_paper_days, source.max_backtest_divergence_pct, source.status,
  CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
(
  paper_order_id STRING NOT NULL,
  signal_id STRING,
  strategy_id STRING NOT NULL,
  strategy_family STRING,
  strategy_version STRING NOT NULL,
  config_version STRING,
  ticker STRING NOT NULL,
  side STRING NOT NULL,
  reference_date DATE NOT NULL,
  signal_timestamp DATETIME,
  expected_entry_price NUMERIC,
  simulated_entry_price NUMERIC,
  simulated_exit_price NUMERIC,
  quantity INT64 NOT NULL,
  notional_brl NUMERIC,
  estimated_cost_pct FLOAT64,
  slippage_pct FLOAT64,
  gross_pnl_pct FLOAT64,
  net_pnl_pct FLOAT64,
  expected_backtest_pnl_pct FLOAT64,
  divergence_pct FLOAT64,
  order_status STRING NOT NULL,
  exit_reason STRING,
  opened_at DATETIME,
  closed_at DATETIME,
  notes STRING,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
PARTITION BY reference_date
CLUSTER BY strategy_id, ticker, order_status
OPTIONS (
  description = "Ordens simuladas do paper trading com preços esperados, execução simulada, custos, slippage e divergência contra backtest"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_strategy_decisions_log`
(
  decision_id STRING NOT NULL,
  event_timestamp DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  strategy_id STRING,
  strategy_version STRING,
  ticker STRING,
  signal_id STRING,
  paper_order_id STRING,
  event_type STRING NOT NULL,
  decision_status STRING NOT NULL,
  reason_code STRING,
  expected_value_pct FLOAT64,
  risk_flag STRING,
  regime_label STRING,
  exposure_action STRING,
  payload_json STRING,
  user_comment STRING,
  created_by STRING NOT NULL,
  created_at DATETIME NOT NULL
)
PARTITION BY reference_date
CLUSTER BY event_type, strategy_id, ticker
OPTIONS (
  description = "Log auditável de decisões automáticas e manuais para o Diário Operacional da Fase 6"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_candidate_signals` AS
WITH active_config AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_config`
  WHERE status = 'em_teste'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY config_id ORDER BY updated_at DESC) = 1
),
latest_exposure AS (
  SELECT
    reference_date,
    market_regime,
    exposure_action,
    max_exposure_pct,
    max_trades,
    risk_per_trade_pct,
    daily_loss_limit_pct
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase4_exposure_recommendation`
),
signals AS (
  SELECT
    s.signal_id,
    s.strategy_id,
    s.strategy_family,
    s.strategy_version,
    s.config_version,
    s.ticker,
    s.side,
    s.reference_date,
    s.signal_timestamp,
    s.expected_entry_price,
    s.metadata_json
  FROM `ingestaokraken.cotacao_intraday.quant_strategy_signals` AS s
  WHERE s.reference_date >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 10 DAY)
)
SELECT
  c.config_id AS paper_config_id,
  c.config_version AS paper_config_version,
  s.*,
  e.market_regime AS regime_label,
  e.exposure_action,
  e.max_exposure_pct AS recommended_exposure_pct,
  COALESCE(e.max_trades, c.max_daily_orders) AS max_trades_per_day,
  c.default_quantity AS suggested_quantity,
  c.default_cost_pct AS estimated_cost_pct,
  c.default_slippage_pct AS estimated_slippage_pct,
  CASE
    WHEN e.exposure_action = 'ficar_em_caixa' THEN 'filtrado_regime_caixa'
    WHEN e.exposure_action = 'bloquear_compras' AND UPPER(s.side) = 'BUY' THEN 'filtrado_bloqueio_compra'
    WHEN e.exposure_action = 'bloquear_vendas' AND UPPER(s.side) = 'SELL' THEN 'filtrado_bloqueio_venda'
    ELSE 'candidato_paper'
  END AS paper_signal_status
FROM signals AS s
CROSS JOIN active_config AS c
LEFT JOIN latest_exposure AS e
  ON e.reference_date = s.reference_date;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_paper_trading_dashboard` AS
WITH orders AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
),
daily AS (
  SELECT
    reference_date,
    COUNTIF(order_status IN ('aberta', 'entrada_simulada')) AS open_orders,
    COUNTIF(order_status IN ('encerrada', 'stop', 'target', 'expire', 'time_stop')) AS closed_orders,
    COUNT(*) AS total_orders,
    SUM(COALESCE(net_pnl_pct, 0)) AS daily_net_pnl_pct,
    AVG(slippage_pct) AS avg_slippage_pct,
    AVG(ABS(divergence_pct)) AS avg_abs_divergence_pct,
    SAFE_DIVIDE(COUNTIF(simulated_entry_price IS NOT NULL), COUNT(*)) AS execution_rate
  FROM orders
  GROUP BY reference_date
),
accumulated AS (
  SELECT
    d.*,
    SUM(d.daily_net_pnl_pct) OVER (ORDER BY d.reference_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS accumulated_net_pnl_pct
  FROM daily AS d
)
SELECT
  a.*,
  CASE
    WHEN total_orders = 0 THEN 'sem_operacoes'
    WHEN avg_abs_divergence_pct > cfg.max_backtest_divergence_pct THEN 'divergencia_alta'
    WHEN execution_rate < 0.80 THEN 'baixa_execucao'
    ELSE 'aderente'
  END AS adherence_status
FROM accumulated AS a
CROSS JOIN `ingestaokraken.cotacao_intraday.quant_paper_trading_config` AS cfg
WHERE cfg.status = 'em_teste';

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_open_orders` AS
SELECT
  paper_order_id,
  signal_id,
  strategy_id,
  strategy_family,
  strategy_version,
  ticker,
  side,
  reference_date,
  expected_entry_price,
  simulated_entry_price,
  quantity,
  notional_brl,
  estimated_cost_pct,
  slippage_pct,
  order_status,
  opened_at,
  notes,
  updated_at
FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
WHERE order_status IN ('aberta', 'entrada_simulada')
ORDER BY opened_at DESC;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_closed_orders_today` AS
SELECT
  paper_order_id,
  strategy_id,
  strategy_version,
  ticker,
  side,
  reference_date,
  simulated_entry_price,
  simulated_exit_price,
  quantity,
  gross_pnl_pct,
  net_pnl_pct,
  expected_backtest_pnl_pct,
  divergence_pct,
  exit_reason,
  closed_at,
  notes
FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
WHERE reference_date = CURRENT_DATE('America/Sao_Paulo')
  AND order_status IN ('encerrada', 'stop', 'target', 'expire', 'time_stop')
ORDER BY closed_at DESC;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_backtest_adherence` AS
SELECT
  strategy_id,
  strategy_family,
  strategy_version,
  ticker,
  COUNT(*) AS paper_trades,
  AVG(expected_backtest_pnl_pct) AS expected_backtest_pnl_pct,
  AVG(net_pnl_pct) AS realized_paper_pnl_pct,
  AVG(slippage_pct) AS avg_slippage_pct,
  AVG(divergence_pct) AS avg_divergence_pct,
  AVG(ABS(divergence_pct)) AS avg_abs_divergence_pct,
  SAFE_DIVIDE(COUNTIF(simulated_entry_price IS NOT NULL), COUNT(*)) AS execution_rate,
  CASE
    WHEN COUNT(*) < 20 THEN 'amostra_paper_insuficiente'
    WHEN AVG(net_pnl_pct) > 0 AND AVG(ABS(divergence_pct)) <= 0.50 THEN 'aderente_positivo'
    WHEN AVG(ABS(divergence_pct)) > 0.50 THEN 'divergencia_explicar'
    ELSE 'paper_negativo'
  END AS adherence_status
FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
WHERE order_status IN ('encerrada', 'stop', 'target', 'expire', 'time_stop')
GROUP BY strategy_id, strategy_family, strategy_version, ticker;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase6_operational_diary` AS
SELECT
  decision_id,
  event_timestamp,
  reference_date,
  strategy_id,
  strategy_version,
  ticker,
  signal_id,
  paper_order_id,
  event_type,
  decision_status,
  reason_code,
  expected_value_pct,
  risk_flag,
  regime_label,
  exposure_action,
  user_comment,
  created_by,
  created_at
FROM `ingestaokraken.cotacao_intraday.quant_strategy_decisions_log`
WHERE reference_date >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 30 DAY)
ORDER BY event_timestamp DESC;
