-- Fase 1 — Motor comum de backtest e métricas para novos sistemas quantitativos.
--
-- Este script define contratos padronizados de sinais, trades e métricas para que
-- qualquer nova estratégia seja comparada pelo mesmo conjunto de regras, custos e
-- indicadores. As tabelas são particionadas por data de referência/saída e
-- clusterizadas pelos identificadores de estratégia para acelerar as telas
-- "Laboratório de Backtests" e "Comparador de Estratégias".

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_strategy_signals`
(
  signal_id STRING NOT NULL,
  strategy_id STRING NOT NULL,
  strategy_family STRING NOT NULL,
  strategy_version STRING NOT NULL,
  config_version STRING,
  ticker STRING NOT NULL,
  signal_timestamp DATETIME NOT NULL,
  reference_date DATE NOT NULL,
  side STRING NOT NULL,
  expected_entry_price FLOAT64 NOT NULL,
  target_price FLOAT64,
  stop_price FLOAT64,
  exit_rule STRING NOT NULL,
  max_horizon_bars INT64 NOT NULL,
  max_horizon_days INT64,
  bar_granularity STRING NOT NULL,
  ranking_score FLOAT64,
  metadata_json STRING,
  created_at DATETIME NOT NULL
)
PARTITION BY reference_date
CLUSTER BY strategy_id, strategy_version, ticker, side
OPTIONS (
  description = "Contrato padronizado de sinais candidatos para o motor quantitativo comum"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_backtest_trades`
(
  trade_id STRING NOT NULL,
  signal_id STRING NOT NULL,
  strategy_id STRING NOT NULL,
  strategy_family STRING NOT NULL,
  strategy_version STRING NOT NULL,
  config_version STRING,
  ticker STRING NOT NULL,
  side STRING NOT NULL,
  reference_date DATE NOT NULL,
  signal_timestamp DATETIME NOT NULL,
  entry_timestamp DATETIME,
  entry_price_expected FLOAT64 NOT NULL,
  entry_price_filled FLOAT64,
  exit_timestamp DATETIME,
  exit_price FLOAT64,
  gross_pnl_pct FLOAT64,
  gross_pnl_value FLOAT64,
  estimated_cost_pct FLOAT64 NOT NULL,
  estimated_cost_value FLOAT64,
  slippage_pct FLOAT64 NOT NULL,
  slippage_value FLOAT64,
  net_pnl_pct FLOAT64,
  net_pnl_value FLOAT64,
  outcome STRING NOT NULL,
  exit_reason STRING NOT NULL,
  bars_in_trade INT64,
  days_in_trade INT64,
  mfe_pct FLOAT64,
  mae_pct FLOAT64,
  regime_label STRING,
  run_id STRING NOT NULL,
  created_at DATETIME NOT NULL
)
PARTITION BY reference_date
CLUSTER BY strategy_id, strategy_version, ticker, outcome
OPTIONS (
  description = "Trades simulados pelo motor quantitativo comum com custos e slippage explícitos"
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_backtest_metrics`
(
  metric_date DATE NOT NULL,
  strategy_id STRING NOT NULL,
  strategy_family STRING NOT NULL,
  strategy_version STRING NOT NULL,
  config_version STRING,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  ticker STRING,
  regime_label STRING,
  side STRING,
  signals INT64 NOT NULL,
  trades INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  win_rate FLOAT64,
  avg_win_pct FLOAT64,
  avg_loss_pct FLOAT64,
  payoff_avg FLOAT64,
  expectancy_net_pct FLOAT64,
  gross_return_pct FLOAT64,
  net_return_pct FLOAT64,
  profit_factor FLOAT64,
  max_drawdown_pct FLOAT64,
  sharpe FLOAT64,
  sortino FLOAT64,
  avg_days_in_trade FLOAT64,
  robustness_score FLOAT64,
  created_at DATETIME NOT NULL
)
PARTITION BY metric_date
CLUSTER BY strategy_id, strategy_version, ticker, regime_label
OPTIONS (
  description = "Métricas consolidadas e comparáveis entre estratégias quantitativas"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_backtest_lab_trades` AS
SELECT
  trade_id,
  signal_id,
  strategy_id,
  strategy_family,
  strategy_version,
  config_version,
  ticker,
  side,
  reference_date,
  signal_timestamp,
  entry_timestamp,
  entry_price_expected,
  entry_price_filled,
  exit_timestamp,
  exit_price,
  gross_pnl_pct,
  estimated_cost_pct,
  slippage_pct,
  net_pnl_pct,
  outcome,
  exit_reason,
  bars_in_trade,
  days_in_trade,
  mfe_pct,
  mae_pct,
  regime_label,
  run_id,
  created_at
FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_backtest_lab_summary` AS
WITH base AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    config_version,
    MIN(reference_date) AS period_start,
    MAX(reference_date) AS period_end,
    COUNT(*) AS signals,
    COUNTIF(entry_timestamp IS NOT NULL) AS trades,
    COUNTIF(entry_timestamp IS NOT NULL AND net_pnl_pct > 0) AS wins,
    COUNTIF(entry_timestamp IS NOT NULL AND net_pnl_pct < 0) AS losses,
    AVG(IF(entry_timestamp IS NOT NULL, net_pnl_pct, NULL)) AS expectancy_net_pct,
    AVG(IF(entry_timestamp IS NOT NULL AND net_pnl_pct > 0, net_pnl_pct, NULL)) AS avg_win_pct,
    AVG(IF(entry_timestamp IS NOT NULL AND net_pnl_pct < 0, net_pnl_pct, NULL)) AS avg_loss_pct,
    SUM(IF(entry_timestamp IS NOT NULL AND net_pnl_pct > 0, net_pnl_pct, 0)) AS gross_wins_pct,
    SUM(IF(entry_timestamp IS NOT NULL AND net_pnl_pct < 0, net_pnl_pct, 0)) AS gross_losses_pct,
    AVG(days_in_trade) AS avg_days_in_trade,
    MAX(created_at) AS last_update
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`
  GROUP BY strategy_id, strategy_family, strategy_version, config_version
)
SELECT
  strategy_id,
  strategy_family,
  strategy_version,
  config_version,
  period_start,
  period_end,
  signals,
  trades,
  wins,
  losses,
  SAFE_DIVIDE(wins, trades) AS win_rate,
  avg_win_pct,
  avg_loss_pct,
  SAFE_DIVIDE(avg_win_pct, ABS(avg_loss_pct)) AS payoff_avg,
  expectancy_net_pct,
  SAFE_DIVIDE(gross_wins_pct, ABS(gross_losses_pct)) AS profit_factor,
  avg_days_in_trade,
  last_update
FROM base;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_strategy_comparator` AS
SELECT
  metric_date,
  strategy_id,
  strategy_family,
  strategy_version,
  config_version,
  period_start,
  period_end,
  ticker,
  regime_label,
  side,
  signals,
  trades,
  win_rate,
  payoff_avg,
  expectancy_net_pct,
  net_return_pct,
  profit_factor,
  max_drawdown_pct,
  sharpe,
  sortino,
  robustness_score,
  CASE
    WHEN trades < 30 THEN 'amostra_insuficiente'
    WHEN expectancy_net_pct <= 0 THEN 'sem_expectativa_positiva'
    WHEN profit_factor < 1 THEN 'profit_factor_fraco'
    WHEN max_drawdown_pct < -0.20 THEN 'drawdown_elevado'
    ELSE 'comparavel'
  END AS comparison_status
FROM `ingestaokraken.cotacao_intraday.quant_backtest_metrics`;
