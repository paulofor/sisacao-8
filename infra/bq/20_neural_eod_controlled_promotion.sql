-- Fase 7 neural EOD — Promoção controlada.
--
-- Registra decisões auditáveis de promoção de modelos neurais para uso
-- controlado. A liberação exige aprovação explícita, robustez fora da amostra,
-- evidência de paper trading e fallback operacional para SIGNAL_SOURCE=heuristic.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_promotion_criteria`
(
  criteria_id STRING NOT NULL,
  criteria_version STRING NOT NULL,
  min_oos_profit_factor FLOAT64 NOT NULL,
  min_oos_win_rate FLOAT64 NOT NULL,
  min_paper_profit_factor FLOAT64 NOT NULL,
  min_paper_win_rate FLOAT64 NOT NULL,
  min_paper_days INT64 NOT NULL,
  min_paper_trades INT64 NOT NULL,
  max_paper_drawdown_pct FLOAT64 NOT NULL,
  min_fill_rate FLOAT64 NOT NULL,
  max_backtest_divergence_pct FLOAT64 NOT NULL,
  min_approvals INT64 NOT NULL,
  require_explicit_approval BOOL NOT NULL,
  promotion_signal_source STRING NOT NULL,
  fallback_signal_source STRING NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY criteria_id, criteria_version, status
OPTIONS (
  description = "Critérios versionados para promoção controlada de modelos neurais EOD com fallback heurístico"
);

MERGE `ingestaokraken.cotacao_intraday.neural_eod_promotion_criteria` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'neural_eod_controlled_promotion' AS criteria_id,
      'v1' AS criteria_version,
      1.15 AS min_oos_profit_factor,
      0.52 AS min_oos_win_rate,
      1.10 AS min_paper_profit_factor,
      0.50 AS min_paper_win_rate,
      120 AS min_paper_days,
      50 AS min_paper_trades,
      0.12 AS max_paper_drawdown_pct,
      0.40 AS min_fill_rate,
      0.05 AS max_backtest_divergence_pct,
      1 AS min_approvals,
      TRUE AS require_explicit_approval,
      'hybrid' AS promotion_signal_source,
      'heuristic' AS fallback_signal_source,
      'active' AS status
    )
  ])
) AS source
ON target.criteria_id = source.criteria_id
  AND target.criteria_version = source.criteria_version
WHEN MATCHED THEN UPDATE SET
  min_oos_profit_factor = source.min_oos_profit_factor,
  min_oos_win_rate = source.min_oos_win_rate,
  min_paper_profit_factor = source.min_paper_profit_factor,
  min_paper_win_rate = source.min_paper_win_rate,
  min_paper_days = source.min_paper_days,
  min_paper_trades = source.min_paper_trades,
  max_paper_drawdown_pct = source.max_paper_drawdown_pct,
  min_fill_rate = source.min_fill_rate,
  max_backtest_divergence_pct = source.max_backtest_divergence_pct,
  min_approvals = source.min_approvals,
  require_explicit_approval = source.require_explicit_approval,
  promotion_signal_source = source.promotion_signal_source,
  fallback_signal_source = source.fallback_signal_source,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  criteria_id, criteria_version, min_oos_profit_factor, min_oos_win_rate,
  min_paper_profit_factor, min_paper_win_rate, min_paper_days, min_paper_trades,
  max_paper_drawdown_pct, min_fill_rate, max_backtest_divergence_pct,
  min_approvals, require_explicit_approval, promotion_signal_source,
  fallback_signal_source, status, created_at, updated_at
) VALUES (
  source.criteria_id, source.criteria_version, source.min_oos_profit_factor,
  source.min_oos_win_rate, source.min_paper_profit_factor,
  source.min_paper_win_rate, source.min_paper_days, source.min_paper_trades,
  source.max_paper_drawdown_pct, source.min_fill_rate,
  source.max_backtest_divergence_pct, source.min_approvals,
  source.require_explicit_approval, source.promotion_signal_source,
  source.fallback_signal_source, source.status, CURRENT_DATETIME(),
  CURRENT_DATETIME()
);

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.neural_eod_promotion_decisions`
(
  promotion_date DATE NOT NULL,
  model_id STRING NOT NULL,
  model_version STRING NOT NULL,
  feature_version STRING,
  criteria_id STRING NOT NULL,
  criteria_version STRING NOT NULL,
  promotion_status STRING NOT NULL,
  effective_signal_source STRING NOT NULL,
  fallback_signal_source STRING NOT NULL,
  oos_profit_factor FLOAT64,
  oos_win_rate FLOAT64,
  paper_profit_factor FLOAT64,
  paper_win_rate FLOAT64,
  paper_days INT64,
  paper_trades INT64,
  paper_max_drawdown_pct FLOAT64,
  fill_rate FLOAT64,
  avg_abs_backtest_divergence_pct FLOAT64,
  approval_count INT64 NOT NULL,
  approvers ARRAY<STRING>,
  approval_ticket STRING,
  failed_criteria ARRAY<STRING>,
  requested_by STRING,
  notes STRING,
  created_at DATETIME NOT NULL
)
PARTITION BY promotion_date
CLUSTER BY model_id, model_version, promotion_status
OPTIONS (
  description = "Decisões auditáveis de promoção controlada de modelos neurais EOD"
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_active_promotion` AS
SELECT *
FROM `ingestaokraken.cotacao_intraday.neural_eod_promotion_decisions`
WHERE promotion_status = 'approved_for_controlled_promotion'
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY model_id
  ORDER BY promotion_date DESC, created_at DESC
) = 1;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_neural_eod_promotion_gate` AS
WITH latest_criteria AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_eod_promotion_criteria`
  WHERE status = 'active'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY criteria_id ORDER BY updated_at DESC) = 1
),
latest_decision AS (
  SELECT *
  FROM `ingestaokraken.cotacao_intraday.neural_eod_promotion_decisions`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY model_id, model_version
    ORDER BY promotion_date DESC, created_at DESC
  ) = 1
)
SELECT
  d.*,
  c.require_explicit_approval,
  c.promotion_signal_source,
  c.fallback_signal_source AS configured_fallback_signal_source,
  CASE
    WHEN d.promotion_status = 'approved_for_controlled_promotion'
      THEN c.promotion_signal_source
    ELSE c.fallback_signal_source
  END AS safe_signal_source
FROM latest_decision AS d
JOIN latest_criteria AS c
  ON c.criteria_id = d.criteria_id
  AND c.criteria_version = d.criteria_version;
