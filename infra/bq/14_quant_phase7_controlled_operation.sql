-- Fase 7 — Preparação para operação controlada.
--
-- Este script prepara a camada de governança para liberar estratégias sobreviventes
-- das fases anteriores para piloto real em escala reduzida. O foco é checklist de
-- aprovação, limites de risco auditáveis, decisões manuais e alertas de desligamento.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_config`
(
  risk_config_id STRING NOT NULL,
  risk_config_version STRING NOT NULL,
  description STRING NOT NULL,
  max_capital_brl NUMERIC NOT NULL,
  max_risk_per_trade_pct FLOAT64 NOT NULL,
  max_daily_loss_pct FLOAT64 NOT NULL,
  max_weekly_loss_pct FLOAT64 NOT NULL,
  max_strategy_exposure_pct FLOAT64 NOT NULL,
  max_ticker_exposure_pct FLOAT64 NOT NULL,
  max_sector_exposure_pct FLOAT64 NOT NULL,
  max_open_positions INT64 NOT NULL,
  auto_pause_on_limit_breach BOOL NOT NULL,
  min_paper_days INT64 NOT NULL,
  min_paper_trades INT64 NOT NULL,
  min_robustness_score FLOAT64 NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY risk_config_id, risk_config_version, status
OPTIONS (
  description = "Configurações versionadas de risco para operação controlada da Fase 7"
);

MERGE `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'controlled_operation_risk_v1' AS risk_config_id,
      'v1' AS risk_config_version,
      'Configuração inicial conservadora para piloto controlado com capital real reduzido e desligamento automático por violação de limites.' AS description,
      NUMERIC '50000.00' AS max_capital_brl,
      0.005 AS max_risk_per_trade_pct,
      0.015 AS max_daily_loss_pct,
      0.030 AS max_weekly_loss_pct,
      0.300 AS max_strategy_exposure_pct,
      0.100 AS max_ticker_exposure_pct,
      0.250 AS max_sector_exposure_pct,
      5 AS max_open_positions,
      TRUE AS auto_pause_on_limit_breach,
      30 AS min_paper_days,
      20 AS min_paper_trades,
      60.0 AS min_robustness_score,
      'ativa' AS status
    )
  ])
) AS source
ON target.risk_config_id = source.risk_config_id
  AND target.risk_config_version = source.risk_config_version
WHEN MATCHED THEN UPDATE SET
  description = source.description,
  max_capital_brl = source.max_capital_brl,
  max_risk_per_trade_pct = source.max_risk_per_trade_pct,
  max_daily_loss_pct = source.max_daily_loss_pct,
  max_weekly_loss_pct = source.max_weekly_loss_pct,
  max_strategy_exposure_pct = source.max_strategy_exposure_pct,
  max_ticker_exposure_pct = source.max_ticker_exposure_pct,
  max_sector_exposure_pct = source.max_sector_exposure_pct,
  max_open_positions = source.max_open_positions,
  auto_pause_on_limit_breach = source.auto_pause_on_limit_breach,
  min_paper_days = source.min_paper_days,
  min_paper_trades = source.min_paper_trades,
  min_robustness_score = source.min_robustness_score,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  risk_config_id, risk_config_version, description, max_capital_brl,
  max_risk_per_trade_pct, max_daily_loss_pct, max_weekly_loss_pct,
  max_strategy_exposure_pct, max_ticker_exposure_pct, max_sector_exposure_pct,
  max_open_positions, auto_pause_on_limit_breach, min_paper_days,
  min_paper_trades, min_robustness_score, status, created_at, updated_at
) VALUES (
  source.risk_config_id, source.risk_config_version, source.description,
  source.max_capital_brl, source.max_risk_per_trade_pct, source.max_daily_loss_pct,
  source.max_weekly_loss_pct, source.max_strategy_exposure_pct,
  source.max_ticker_exposure_pct, source.max_sector_exposure_pct,
  source.max_open_positions, source.auto_pause_on_limit_breach,
  source.min_paper_days, source.min_paper_trades, source.min_robustness_score,
  source.status, CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_strategy_approval_checklist`
(
  approval_id STRING NOT NULL,
  strategy_id STRING NOT NULL,
  strategy_family STRING,
  strategy_version STRING NOT NULL,
  risk_config_version STRING NOT NULL,
  approval_status STRING NOT NULL,
  min_sample_ok BOOL NOT NULL,
  positive_expectancy_ok BOOL NOT NULL,
  drawdown_ok BOOL NOT NULL,
  oos_validation_ok BOOL NOT NULL,
  robustness_ok BOOL NOT NULL,
  paper_trading_ok BOOL NOT NULL,
  risk_limits_ok BOOL NOT NULL,
  manual_decision STRING NOT NULL,
  decided_by STRING,
  decision_reason STRING,
  decided_at DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY strategy_id, strategy_version, approval_status
OPTIONS (
  description = "Checklist auditável de liberação de estratégias para piloto controlado"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_snapshots`
(
  snapshot_id STRING NOT NULL,
  snapshot_timestamp DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  strategy_id STRING,
  strategy_version STRING,
  ticker STRING,
  sector STRING,
  current_exposure_brl NUMERIC,
  current_exposure_pct FLOAT64,
  daily_pnl_pct FLOAT64,
  weekly_pnl_pct FLOAT64,
  open_positions INT64,
  risk_per_trade_pct FLOAT64,
  breached_limit STRING,
  alert_level STRING NOT NULL,
  recommended_action STRING NOT NULL,
  created_at DATETIME NOT NULL
)
PARTITION BY reference_date
CLUSTER BY strategy_id, ticker, alert_level
OPTIONS (
  description = "Snapshots de exposição, PnL e violações de limite para a tela Risco e Limites"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_strategy_committee_decisions`
(
  committee_decision_id STRING NOT NULL,
  decision_timestamp DATETIME NOT NULL,
  strategy_id STRING NOT NULL,
  strategy_version STRING NOT NULL,
  previous_status STRING,
  new_status STRING NOT NULL,
  decision_type STRING NOT NULL,
  decided_by STRING NOT NULL,
  decision_reason STRING NOT NULL,
  effective_from DATETIME,
  effective_until DATETIME,
  created_at DATETIME NOT NULL
)
PARTITION BY DATE(decision_timestamp)
CLUSTER BY strategy_id, strategy_version, new_status
OPTIONS (
  description = "Decisões manuais do Comitê de Estratégias: aprovar, pausar, reprovar ou retomar"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase7_strategy_committee` AS
WITH risk_cfg AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_config`
  WHERE status = 'ativa'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY risk_config_id ORDER BY updated_at DESC) = 1
),
backtest AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    SUM(trades) AS trades,
    AVG(expectancy_net_pct) AS expectancy_net_pct,
    AVG(profit_factor) AS profit_factor,
    MIN(max_drawdown_pct) AS max_drawdown_pct
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_metrics`
  GROUP BY strategy_id, strategy_family, strategy_version
),
robustness AS (
  SELECT
    strategy_id,
    strategy_version,
    MAX(robustness_score) AS robustness_score,
    MAX(IF(oos_status = 'aprovado_oos', 1, 0)) = 1 AS oos_validation_ok
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase5_robustness_dashboard`
  GROUP BY strategy_id, strategy_version
),
paper AS (
  SELECT
    strategy_id,
    strategy_version,
    COUNT(DISTINCT reference_date) AS paper_days,
    COUNT(*) AS paper_trades,
    AVG(net_pnl_pct) AS paper_expectancy_net_pct,
    AVG(ABS(divergence_pct)) AS avg_abs_divergence_pct
  FROM `ingestaokraken.cotacao_intraday.quant_paper_trading_orders`
  WHERE order_status IN ('encerrada', 'stop', 'target', 'expire', 'time_stop')
  GROUP BY strategy_id, strategy_version
),
checklist AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_strategy_approval_checklist`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY strategy_id, strategy_version ORDER BY updated_at DESC) = 1
)
SELECT
  b.strategy_id,
  b.strategy_family,
  b.strategy_version,
  COALESCE(c.approval_status, 'pesquisa') AS approval_status,
  b.trades,
  b.expectancy_net_pct,
  b.profit_factor,
  b.max_drawdown_pct,
  r.robustness_score,
  p.paper_days,
  p.paper_trades,
  p.paper_expectancy_net_pct,
  p.avg_abs_divergence_pct,
  b.trades >= 30 AS min_sample_ok,
  b.expectancy_net_pct > 0 AS positive_expectancy_ok,
  b.max_drawdown_pct >= -0.20 AS drawdown_ok,
  COALESCE(r.oos_validation_ok, FALSE) AS oos_validation_ok,
  COALESCE(r.robustness_score, 0) >= cfg.min_robustness_score AS robustness_ok,
  COALESCE(p.paper_days, 0) >= cfg.min_paper_days
    AND COALESCE(p.paper_trades, 0) >= cfg.min_paper_trades
    AND COALESCE(p.paper_expectancy_net_pct, -999) > 0 AS paper_trading_ok,
  COALESCE(c.risk_limits_ok, FALSE) AS risk_limits_ok,
  COALESCE(c.manual_decision, 'pendente') AS manual_decision,
  CASE
    WHEN COALESCE(c.manual_decision, 'pendente') = 'reprovar' THEN 'reprovada'
    WHEN COALESCE(c.manual_decision, 'pendente') = 'pausar' THEN 'pausada'
    WHEN b.trades >= 30
      AND b.expectancy_net_pct > 0
      AND b.max_drawdown_pct >= -0.20
      AND COALESCE(r.oos_validation_ok, FALSE)
      AND COALESCE(r.robustness_score, 0) >= cfg.min_robustness_score
      AND COALESCE(p.paper_days, 0) >= cfg.min_paper_days
      AND COALESCE(p.paper_trades, 0) >= cfg.min_paper_trades
      AND COALESCE(p.paper_expectancy_net_pct, -999) > 0
      AND COALESCE(c.risk_limits_ok, FALSE)
      AND COALESCE(c.manual_decision, 'pendente') = 'aprovar'
      THEN 'piloto'
    WHEN COALESCE(p.paper_days, 0) > 0 THEN 'paper_trading'
    WHEN COALESCE(r.robustness_score, 0) > 0 THEN 'validacao'
    ELSE 'pesquisa'
  END AS recommended_status
FROM backtest AS b
CROSS JOIN risk_cfg AS cfg
LEFT JOIN robustness AS r
  ON r.strategy_id = b.strategy_id AND r.strategy_version = b.strategy_version
LEFT JOIN paper AS p
  ON p.strategy_id = b.strategy_id AND p.strategy_version = b.strategy_version
LEFT JOIN checklist AS c
  ON c.strategy_id = b.strategy_id AND c.strategy_version = b.strategy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase7_risk_limits` AS
WITH cfg AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_config`
  WHERE status = 'ativa'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY risk_config_id ORDER BY updated_at DESC) = 1
),
latest AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_controlled_operation_risk_snapshots`
  WHERE reference_date >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 7 DAY)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY COALESCE(strategy_id, '_ALL_'), COALESCE(ticker, '_ALL_'), COALESCE(sector, '_ALL_')
    ORDER BY snapshot_timestamp DESC
  ) = 1
)
SELECT
  l.snapshot_timestamp,
  l.reference_date,
  l.strategy_id,
  l.strategy_version,
  l.ticker,
  l.sector,
  l.current_exposure_brl,
  l.current_exposure_pct,
  l.daily_pnl_pct,
  l.weekly_pnl_pct,
  l.open_positions,
  l.risk_per_trade_pct,
  cfg.max_capital_brl,
  cfg.max_risk_per_trade_pct,
  cfg.max_daily_loss_pct,
  cfg.max_weekly_loss_pct,
  cfg.max_strategy_exposure_pct,
  cfg.max_ticker_exposure_pct,
  cfg.max_sector_exposure_pct,
  cfg.max_open_positions,
  l.breached_limit,
  CASE
    WHEN l.breached_limit IS NOT NULL THEN 'limite_violado'
    WHEN l.daily_pnl_pct <= -0.80 * cfg.max_daily_loss_pct THEN 'perto_limite_diario'
    WHEN l.weekly_pnl_pct <= -0.80 * cfg.max_weekly_loss_pct THEN 'perto_limite_semanal'
    WHEN l.open_positions >= cfg.max_open_positions THEN 'limite_posicoes_atingido'
    ELSE 'dentro_dos_limites'
  END AS risk_status,
  CASE
    WHEN l.breached_limit IS NOT NULL AND cfg.auto_pause_on_limit_breach THEN 'pausar_estrategia_imediatamente'
    WHEN l.breached_limit IS NOT NULL THEN 'bloquear_novas_ordens'
    WHEN l.daily_pnl_pct <= -0.80 * cfg.max_daily_loss_pct THEN 'reduzir_exposicao'
    ELSE 'monitorar'
  END AS recommended_action,
  l.alert_level,
  l.created_at
FROM latest AS l
CROSS JOIN cfg;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase7_shutdown_alerts` AS
SELECT
  snapshot_timestamp,
  reference_date,
  strategy_id,
  strategy_version,
  ticker,
  sector,
  breached_limit,
  alert_level,
  recommended_action,
  current_exposure_pct,
  daily_pnl_pct,
  weekly_pnl_pct,
  open_positions
FROM `ingestaokraken.cotacao_intraday.vw_quant_phase7_risk_limits`
WHERE risk_status IN ('limite_violado', 'perto_limite_diario', 'perto_limite_semanal', 'limite_posicoes_atingido')
ORDER BY snapshot_timestamp DESC;
