-- Fase 2 — Execução operacional das baselines preparadas.
--
-- Este script materializa uma janela histórica controlada de sinais candidatos em
-- quant_strategy_signals e roda uma simulação diária simples, baseada em candles
-- OHLCV, para popular quant_backtest_trades e quant_backtest_metrics. Ele é
-- idempotente para config_version = 'phase2_baseline' e pode ser reexecutado
-- após atualizar as views da Fase 2.

DECLARE run_id STRING DEFAULT CONCAT('phase2_baseline_', FORMAT_DATETIME('%Y%m%d%H%M%S', CURRENT_DATETIME()));
DECLARE lookback_days INT64 DEFAULT 365;

MERGE `ingestaokraken.cotacao_intraday.quant_strategy_signals` AS target
USING (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_baseline_signal_candidates`
  WHERE reference_date >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_days DAY)
) AS source
ON target.signal_id = source.signal_id
WHEN MATCHED THEN UPDATE SET
  strategy_family = source.strategy_family,
  strategy_version = source.strategy_version,
  config_version = source.config_version,
  ticker = source.ticker,
  signal_timestamp = source.signal_timestamp,
  reference_date = source.reference_date,
  side = source.side,
  expected_entry_price = source.expected_entry_price,
  target_price = source.target_price,
  stop_price = source.stop_price,
  exit_rule = source.exit_rule,
  max_horizon_bars = source.max_horizon_bars,
  max_horizon_days = source.max_horizon_days,
  bar_granularity = source.bar_granularity,
  ranking_score = source.ranking_score,
  metadata_json = source.metadata_json,
  created_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  signal_id, strategy_id, strategy_family, strategy_version, config_version,
  ticker, signal_timestamp, reference_date, side, expected_entry_price,
  target_price, stop_price, exit_rule, max_horizon_bars, max_horizon_days,
  bar_granularity, ranking_score, metadata_json, created_at
) VALUES (
  source.signal_id, source.strategy_id, source.strategy_family, source.strategy_version, source.config_version,
  source.ticker, source.signal_timestamp, source.reference_date, source.side, source.expected_entry_price,
  source.target_price, source.stop_price, source.exit_rule, source.max_horizon_bars, source.max_horizon_days,
  source.bar_granularity, source.ranking_score, source.metadata_json, CURRENT_DATETIME()
);

DELETE FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`
WHERE config_version = 'phase2_baseline'
  AND reference_date >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_days DAY);

INSERT INTO `ingestaokraken.cotacao_intraday.quant_backtest_trades` (
  trade_id, signal_id, strategy_id, strategy_family, strategy_version, config_version,
  ticker, side, reference_date, signal_timestamp, entry_timestamp, entry_price_expected,
  entry_price_filled, exit_timestamp, exit_price, gross_pnl_pct, gross_pnl_value,
  estimated_cost_pct, estimated_cost_value, slippage_pct, slippage_value,
  net_pnl_pct, net_pnl_value, outcome, exit_reason, bars_in_trade, days_in_trade,
  mfe_pct, mae_pct, regime_label, run_id, created_at
)
WITH signals AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_strategy_signals`
  WHERE config_version = 'phase2_baseline'
    AND reference_date >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_days DAY)
), future_bars AS (
  SELECT
    s.*,
    d.data_pregao AS bar_date,
    d.open,
    d.high,
    d.low,
    d.close,
    ROW_NUMBER() OVER (PARTITION BY s.signal_id ORDER BY d.data_pregao) AS bar_number
  FROM signals AS s
  JOIN `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario` AS d
    ON d.ticker = s.ticker
   AND d.data_pregao > s.reference_date
   AND d.data_pregao <= DATE_ADD(s.reference_date, INTERVAL s.max_horizon_days + 10 DAY)
  QUALIFY bar_number <= s.max_horizon_days
), exit_candidates AS (
  SELECT
    *,
    CASE
      WHEN side = 'BUY' AND target_price IS NOT NULL AND high >= target_price THEN 'target'
      WHEN side = 'BUY' AND stop_price IS NOT NULL AND low <= stop_price THEN 'stop'
      WHEN side = 'SELL' AND target_price IS NOT NULL AND low <= target_price THEN 'target'
      WHEN side = 'SELL' AND stop_price IS NOT NULL AND high >= stop_price THEN 'stop'
      WHEN bar_number = max_horizon_days THEN 'expiration'
      ELSE NULL
    END AS candidate_exit_reason,
    CASE
      WHEN side = 'BUY' AND target_price IS NOT NULL AND high >= target_price THEN target_price
      WHEN side = 'BUY' AND stop_price IS NOT NULL AND low <= stop_price THEN stop_price
      WHEN side = 'SELL' AND target_price IS NOT NULL AND low <= target_price THEN target_price
      WHEN side = 'SELL' AND stop_price IS NOT NULL AND high >= stop_price THEN stop_price
      WHEN bar_number = max_horizon_days THEN close
      ELSE NULL
    END AS candidate_exit_price
  FROM future_bars
), selected_exit AS (
  SELECT *
  FROM exit_candidates
  WHERE candidate_exit_reason IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY signal_id ORDER BY bar_number) = 1
), excursions AS (
  SELECT
    signal_id,
    MAX(IF(side = 'BUY', SAFE_DIVIDE(high, expected_entry_price) - 1, SAFE_DIVIDE(expected_entry_price, low) - 1)) AS mfe_pct,
    MIN(IF(side = 'BUY', SAFE_DIVIDE(low, expected_entry_price) - 1, SAFE_DIVIDE(expected_entry_price, high) - 1)) AS mae_pct
  FROM future_bars
  GROUP BY signal_id
)
SELECT
  CONCAT('trade:', s.signal_id) AS trade_id,
  s.signal_id,
  s.strategy_id,
  s.strategy_family,
  s.strategy_version,
  s.config_version,
  s.ticker,
  s.side,
  s.reference_date,
  s.signal_timestamp,
  DATETIME(MIN(f.bar_date), TIME '10:00:00') AS entry_timestamp,
  s.expected_entry_price AS entry_price_expected,
  s.expected_entry_price AS entry_price_filled,
  DATETIME(se.bar_date, TIME '18:00:00') AS exit_timestamp,
  se.candidate_exit_price AS exit_price,
  IF(s.side = 'BUY', SAFE_DIVIDE(se.candidate_exit_price, s.expected_entry_price) - 1, SAFE_DIVIDE(s.expected_entry_price, se.candidate_exit_price) - 1) AS gross_pnl_pct,
  IF(s.side = 'BUY', SAFE_DIVIDE(se.candidate_exit_price, s.expected_entry_price) - 1, SAFE_DIVIDE(s.expected_entry_price, se.candidate_exit_price) - 1) AS gross_pnl_value,
  0.001 AS estimated_cost_pct,
  0.001 AS estimated_cost_value,
  0.0005 AS slippage_pct,
  0.0005 AS slippage_value,
  IF(s.side = 'BUY', SAFE_DIVIDE(se.candidate_exit_price, s.expected_entry_price) - 1, SAFE_DIVIDE(s.expected_entry_price, se.candidate_exit_price) - 1) - 0.0015 AS net_pnl_pct,
  IF(s.side = 'BUY', SAFE_DIVIDE(se.candidate_exit_price, s.expected_entry_price) - 1, SAFE_DIVIDE(s.expected_entry_price, se.candidate_exit_price) - 1) - 0.0015 AS net_pnl_value,
  CASE
    WHEN se.candidate_exit_reason = 'target' THEN 'WIN'
    WHEN se.candidate_exit_reason = 'stop' THEN 'LOSS'
    WHEN IF(s.side = 'BUY', SAFE_DIVIDE(se.candidate_exit_price, s.expected_entry_price) - 1, SAFE_DIVIDE(s.expected_entry_price, se.candidate_exit_price) - 1) > 0 THEN 'WIN'
    ELSE 'LOSS'
  END AS outcome,
  se.candidate_exit_reason AS exit_reason,
  se.bar_number AS bars_in_trade,
  DATE_DIFF(se.bar_date, s.reference_date, DAY) AS days_in_trade,
  e.mfe_pct,
  e.mae_pct,
  CAST(NULL AS STRING) AS regime_label,
  run_id,
  CURRENT_DATETIME() AS created_at
FROM signals AS s
JOIN future_bars AS f ON f.signal_id = s.signal_id
JOIN selected_exit AS se ON se.signal_id = s.signal_id
LEFT JOIN excursions AS e ON e.signal_id = s.signal_id
GROUP BY
  s.signal_id, s.strategy_id, s.strategy_family, s.strategy_version, s.config_version,
  s.ticker, s.side, s.reference_date, s.signal_timestamp, s.expected_entry_price,
  se.bar_date, se.candidate_exit_price, se.candidate_exit_reason, se.bar_number,
  e.mfe_pct, e.mae_pct;

DELETE FROM `ingestaokraken.cotacao_intraday.quant_backtest_metrics`
WHERE config_version = 'phase2_baseline'
  AND metric_date = CURRENT_DATE();

INSERT INTO `ingestaokraken.cotacao_intraday.quant_backtest_metrics` (
  metric_date, strategy_id, strategy_family, strategy_version, config_version,
  period_start, period_end, ticker, regime_label, side, signals, trades, wins,
  losses, win_rate, avg_win_pct, avg_loss_pct, payoff_avg, expectancy_net_pct,
  gross_return_pct, net_return_pct, profit_factor, max_drawdown_pct, sharpe,
  sortino, avg_days_in_trade, robustness_score, created_at
)
WITH trades AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.quant_backtest_trades`
  WHERE config_version = 'phase2_baseline'
    AND reference_date >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_days DAY)
), grouped AS (
  SELECT
    strategy_id,
    strategy_family,
    strategy_version,
    config_version,
    MIN(reference_date) AS period_start,
    MAX(reference_date) AS period_end,
    CAST(NULL AS STRING) AS ticker,
    CAST(NULL AS STRING) AS regime_label,
    side,
    COUNT(*) AS signals,
    COUNT(*) AS trades,
    COUNTIF(net_pnl_pct > 0) AS wins,
    COUNTIF(net_pnl_pct <= 0) AS losses,
    AVG(IF(net_pnl_pct > 0, net_pnl_pct, NULL)) AS avg_win_pct,
    AVG(IF(net_pnl_pct <= 0, net_pnl_pct, NULL)) AS avg_loss_pct,
    AVG(net_pnl_pct) AS expectancy_net_pct,
    SUM(gross_pnl_pct) AS gross_return_pct,
    SUM(net_pnl_pct) AS net_return_pct,
    SUM(IF(net_pnl_pct > 0, net_pnl_pct, 0)) AS gross_wins_pct,
    SUM(IF(net_pnl_pct < 0, net_pnl_pct, 0)) AS gross_losses_pct,
    MIN(net_pnl_pct) AS max_drawdown_pct,
    SAFE_DIVIDE(AVG(net_pnl_pct), NULLIF(STDDEV_POP(net_pnl_pct), 0)) AS sharpe,
    SAFE_DIVIDE(AVG(net_pnl_pct), NULLIF(STDDEV_POP(IF(net_pnl_pct < 0, net_pnl_pct, NULL)), 0)) AS sortino,
    AVG(days_in_trade) AS avg_days_in_trade
  FROM trades
  GROUP BY strategy_id, strategy_family, strategy_version, config_version, side
)
SELECT
  CURRENT_DATE() AS metric_date,
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
  wins,
  losses,
  SAFE_DIVIDE(wins, trades) AS win_rate,
  avg_win_pct,
  avg_loss_pct,
  SAFE_DIVIDE(avg_win_pct, ABS(avg_loss_pct)) AS payoff_avg,
  expectancy_net_pct,
  gross_return_pct,
  net_return_pct,
  SAFE_DIVIDE(gross_wins_pct, ABS(gross_losses_pct)) AS profit_factor,
  max_drawdown_pct,
  sharpe,
  sortino,
  avg_days_in_trade,
  LEAST(1.0, GREATEST(0.0, 0.5 + COALESCE(expectancy_net_pct, 0) * 10 + COALESCE(SAFE_DIVIDE(wins, trades), 0) - 0.5)) AS robustness_score,
  CURRENT_DATETIME() AS created_at
FROM grouped;
