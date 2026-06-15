-- Fase 2 — Sistemas baseline simples para novos sistemas quantitativos.
--
-- Este script prepara as hipóteses baseline descritas no plano quantitativo.
-- As views abaixo geram sinais candidatos auditáveis a partir dos candles diários
-- elegíveis da Fase 0 e usam o contrato comum de sinais/trades/métricas da Fase 1.

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.quant_baseline_strategy_config`
(
  strategy_id STRING NOT NULL,
  strategy_family STRING NOT NULL,
  strategy_version STRING NOT NULL,
  hypothesis STRING NOT NULL,
  side STRING NOT NULL,
  entry_rule STRING NOT NULL,
  exit_rule STRING NOT NULL,
  max_horizon_days INT64 NOT NULL,
  target_pct FLOAT64,
  stop_pct FLOAT64,
  parameters_json STRING NOT NULL,
  status STRING NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
CLUSTER BY strategy_id, strategy_version, status
OPTIONS (
  description = "Catálogo auditável das estratégias baseline simples da Fase 2"
);

MERGE `ingestaokraken.cotacao_intraday.quant_baseline_strategy_config` AS target
USING (
  SELECT * FROM UNNEST([
    STRUCT(
      'baseline_daily_momentum_v1' AS strategy_id,
      'momentum_diario' AS strategy_family,
      'v1' AS strategy_version,
      'Ativos com retorno recente positivo e volume relativo elevado tendem a continuar no curto prazo.' AS hypothesis,
      'BUY' AS side,
      'close > close_5d_ago AND close > sma_20 AND volume_financeiro > avg_volume_20d' AS entry_rule,
      'Saída por alvo, stop ou expiração em 5 pregões.' AS exit_rule,
      5 AS max_horizon_days,
      0.04 AS target_pct,
      0.02 AS stop_pct,
      '{"lookback_return_days":5,"trend_sma_days":20,"volume_avg_days":20,"min_return_5d":0.02}' AS parameters_json,
      'em_teste' AS status
    ),
    STRUCT(
      'baseline_daily_mean_reversion_v1', 'reversao_media_diaria', 'v1',
      'Quedas curtas e fortes em ativos ainda acima da média de tendência podem reverter parcialmente.',
      'BUY',
      'return_3d <= -0.04 AND close > sma_50 AND rsi_14 <= 35',
      'Saída por alvo, stop ou expiração em 3 pregões.',
      3, 0.03, 0.025,
      '{"lookback_return_days":3,"trend_sma_days":50,"rsi_days":14,"max_rsi":35,"max_return_3d":-0.04}',
      'em_teste'
    ),
    STRUCT(
      'baseline_daily_breakout_v1', 'rompimento_diario', 'v1',
      'Rompimentos de máxima de 20 pregões com volume acima da média indicam entrada de fluxo comprador.',
      'BUY',
      'close > prior_high_20d AND volume_financeiro >= 1.5 * avg_volume_20d',
      'Saída por alvo, stop ou expiração em 5 pregões.',
      5, 0.05, 0.025,
      '{"breakout_days":20,"volume_avg_days":20,"min_relative_volume":1.5}',
      'em_teste'
    ),
    STRUCT(
      'baseline_gap_continuation_v1', 'gap_continuation', 'v1',
      'Gaps positivos com fechamento sustentado acima da abertura podem continuar no curto prazo.',
      'BUY',
      'open >= prior_close * 1.015 AND close > open',
      'Saída por alvo, stop ou expiração em 2 pregões.',
      2, 0.025, 0.02,
      '{"min_gap_pct":0.015,"confirmation":"close_above_open"}',
      'em_teste'
    ),
    STRUCT(
      'baseline_gap_fade_v1', 'gap_fade', 'v1',
      'Gaps positivos excessivos que fecham fracos podem devolver parte do movimento.',
      'SELL',
      'open >= prior_close * 1.03 AND close < open',
      'Saída por alvo, stop ou expiração em 2 pregões.',
      2, 0.025, 0.02,
      '{"min_gap_pct":0.03,"confirmation":"close_below_open"}',
      'em_teste'
    ),
    STRUCT(
      'baseline_relative_strength_ranking_v1', 'ranking_forca_relativa', 'v1',
      'Comprar os ativos com melhor combinação diária de força relativa, tendência e volume relativo.',
      'BUY',
      'Selecionar top 5 por score composto no universo elegível.',
      'Saída por rebalanceamento diário ou expiração em 5 pregões.',
      5, 0.04, 0.025,
      '{"top_n":5,"return_20d_weight":0.45,"return_5d_weight":0.30,"relative_volume_weight":0.15,"trend_weight":0.10}',
      'em_teste'
    ),
    STRUCT(
      'baseline_ibov_regime_filter_v1', 'regime_ibovespa', 'v1',
      'Operar comprado apenas quando o proxy do índice está em regime favorável reduz sinais em ambientes hostis.',
      'BUY',
      'regime = favoravel AND close > sma_20',
      'Filtro de ativação para outras baselines; sem trade isolado obrigatório.',
      5, NULL, NULL,
      '{"index_ticker_candidates":["IBOV","BOVA11"],"sma_fast_days":20,"sma_slow_days":50}',
      'em_teste'
    )
  ])
) AS source
ON target.strategy_id = source.strategy_id AND target.strategy_version = source.strategy_version
WHEN MATCHED THEN UPDATE SET
  strategy_family = source.strategy_family,
  hypothesis = source.hypothesis,
  side = source.side,
  entry_rule = source.entry_rule,
  exit_rule = source.exit_rule,
  max_horizon_days = source.max_horizon_days,
  target_pct = source.target_pct,
  stop_pct = source.stop_pct,
  parameters_json = source.parameters_json,
  status = source.status,
  updated_at = CURRENT_DATETIME()
WHEN NOT MATCHED THEN INSERT (
  strategy_id, strategy_family, strategy_version, hypothesis, side, entry_rule,
  exit_rule, max_horizon_days, target_pct, stop_pct, parameters_json,
  status, created_at, updated_at
) VALUES (
  source.strategy_id, source.strategy_family, source.strategy_version, source.hypothesis, source.side,
  source.entry_rule, source.exit_rule, source.max_horizon_days, source.target_pct, source.stop_pct,
  source.parameters_json, source.status, CURRENT_DATETIME(), CURRENT_DATETIME()
);

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase2_daily_features` AS
WITH research_universe AS (
  SELECT ticker
  FROM `ingestaokraken.cotacao_intraday.vw_quant_ticker_coverage`
  WHERE eligibility_status = 'elegivel'
    OR (
      eligibility_status = 'observacao'
      AND coverage_pct >= 0.90
      AND avg_financial_volume >= 1000000
      AND invalid_price_days = 0
      AND invalid_volume_days = 0
      AND duplicate_days <= 3
    )
),
daily_dedup AS (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT
      d.*,
      ROW_NUMBER() OVER (
        PARTITION BY d.ticker, d.data_pregao
        ORDER BY d.atualizado_em DESC
      ) AS row_num
    FROM `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario` AS d
  )
  WHERE row_num = 1
),
raw AS (
  SELECT
    d.ticker,
    d.data_pregao AS reference_date,
    d.open,
    d.high,
    d.low,
    d.close,
    d.volume_financeiro,
    LAG(d.close, 1) OVER ticker_window AS prior_close,
    LAG(d.close, 3) OVER ticker_window AS close_3d_ago,
    LAG(d.close, 5) OVER ticker_window AS close_5d_ago,
    LAG(d.close, 20) OVER ticker_window AS close_20d_ago,
    d.close - LAG(d.close, 1) OVER ticker_window AS close_delta
  FROM daily_dedup AS d
  INNER JOIN research_universe AS e ON e.ticker = d.ticker
  WINDOW ticker_window AS (PARTITION BY d.ticker ORDER BY d.data_pregao)
),
base AS (
  SELECT
    *,
    AVG(close) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
    AVG(close) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
    AVG(volume_financeiro) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS avg_volume_20d,
    MAX(high) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS prior_high_20d,
    MIN(low) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS prior_low_20d,
    AVG(GREATEST(close_delta, 0)) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_gain_14,
    AVG(ABS(LEAST(close_delta, 0))) OVER (PARTITION BY ticker ORDER BY reference_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_loss_14
  FROM raw
)
SELECT
  * EXCEPT(close_delta),
  SAFE_DIVIDE(close, close_3d_ago) - 1 AS return_3d,
  SAFE_DIVIDE(close, close_5d_ago) - 1 AS return_5d,
  SAFE_DIVIDE(close, close_20d_ago) - 1 AS return_20d,
  SAFE_DIVIDE(volume_financeiro, avg_volume_20d) AS relative_volume_20d,
  100 - SAFE_DIVIDE(100, 1 + SAFE_DIVIDE(avg_gain_14, NULLIF(avg_loss_14, 0))) AS rsi_14,
  SAFE_DIVIDE(open, prior_close) - 1 AS gap_pct
FROM base;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase2_baseline_signal_candidates` AS
WITH features AS (
  SELECT * FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_daily_features`
),
ranking AS (
  SELECT
    *,
    0.45 * PERCENT_RANK() OVER (PARTITION BY reference_date ORDER BY return_20d)
      + 0.30 * PERCENT_RANK() OVER (PARTITION BY reference_date ORDER BY return_5d)
      + 0.15 * PERCENT_RANK() OVER (PARTITION BY reference_date ORDER BY relative_volume_20d)
      + 0.10 * IF(close > sma_20, 1, 0) AS relative_strength_score
  FROM features
),
signals AS (
  SELECT 'baseline_daily_momentum_v1' AS strategy_id, 'momentum_diario' AS strategy_family, 'v1' AS strategy_version,
    ticker, reference_date, 'BUY' AS side, close AS expected_entry_price, close * 1.04 AS target_price, close * 0.98 AS stop_price,
    'target_stop_or_5_days' AS exit_rule, 5 AS max_horizon_days, relative_volume_20d AS ranking_score,
    TO_JSON_STRING(STRUCT(return_5d, sma_20, relative_volume_20d, rsi_14)) AS metadata_json
  FROM features
  WHERE return_5d >= 0.02 AND close > sma_20 AND volume_financeiro > avg_volume_20d
  UNION ALL
  SELECT 'baseline_daily_mean_reversion_v1', 'reversao_media_diaria', 'v1', ticker, reference_date, 'BUY', close, close * 1.03, close * 0.975,
    'target_stop_or_3_days', 3, ABS(return_3d), TO_JSON_STRING(STRUCT(return_3d, sma_50, rsi_14))
  FROM features
  WHERE return_3d <= -0.04 AND close > sma_50 AND rsi_14 <= 35
  UNION ALL
  SELECT 'baseline_daily_breakout_v1', 'rompimento_diario', 'v1', ticker, reference_date, 'BUY', close, close * 1.05, close * 0.975,
    'target_stop_or_5_days', 5, relative_volume_20d, TO_JSON_STRING(STRUCT(prior_high_20d, relative_volume_20d))
  FROM features
  WHERE close > prior_high_20d AND volume_financeiro >= 1.5 * avg_volume_20d
  UNION ALL
  SELECT 'baseline_gap_continuation_v1', 'gap_continuation', 'v1', ticker, reference_date, 'BUY', close, close * 1.025, close * 0.98,
    'target_stop_or_2_days', 2, gap_pct, TO_JSON_STRING(STRUCT(gap_pct, open, close, prior_close))
  FROM features
  WHERE open >= prior_close * 1.015 AND close > open
  UNION ALL
  SELECT 'baseline_gap_fade_v1', 'gap_fade', 'v1', ticker, reference_date, 'SELL', close, close * 0.975, close * 1.02,
    'target_stop_or_2_days', 2, gap_pct, TO_JSON_STRING(STRUCT(gap_pct, open, close, prior_close))
  FROM features
  WHERE open >= prior_close * 1.03 AND close < open
  UNION ALL
  SELECT 'baseline_relative_strength_ranking_v1', 'ranking_forca_relativa', 'v1', ticker, reference_date, 'BUY', close, close * 1.04, close * 0.975,
    'rebalance_or_5_days', 5, relative_strength_score, TO_JSON_STRING(STRUCT(return_20d, return_5d, relative_volume_20d, close, sma_20))
  FROM ranking
  QUALIFY ROW_NUMBER() OVER (PARTITION BY reference_date ORDER BY relative_strength_score DESC, volume_financeiro DESC) <= 5
)
SELECT
  FARM_FINGERPRINT(CONCAT(strategy_id, '|', ticker, '|', CAST(reference_date AS STRING), '|', side)) AS signal_fingerprint,
  CONCAT(strategy_id, ':', ticker, ':', CAST(reference_date AS STRING), ':', side) AS signal_id,
  strategy_id,
  strategy_family,
  strategy_version,
  'phase2_baseline' AS config_version,
  ticker,
  DATETIME(reference_date, TIME '18:00:00') AS signal_timestamp,
  reference_date,
  side,
  expected_entry_price,
  target_price,
  stop_price,
  exit_rule,
  max_horizon_days AS max_horizon_bars,
  max_horizon_days,
  '1d' AS bar_granularity,
  ranking_score,
  metadata_json,
  CURRENT_DATETIME() AS created_at
FROM signals;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase2_baseline_status` AS
WITH signal_counts AS (
  SELECT strategy_id, strategy_version, COUNT(*) AS generated_signals, COUNT(DISTINCT reference_date) AS signal_days, MAX(reference_date) AS last_signal_date
  FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_baseline_signal_candidates`
  GROUP BY strategy_id, strategy_version
),
metrics AS (
  SELECT strategy_id, strategy_version, trades, expectancy_net_pct, profit_factor, max_drawdown_pct, robustness_score
  FROM `ingestaokraken.cotacao_intraday.vw_quant_strategy_comparator`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY strategy_id, strategy_version ORDER BY metric_date DESC) = 1
)
SELECT
  c.strategy_id,
  c.strategy_family,
  c.strategy_version,
  c.hypothesis,
  c.status AS configured_status,
  COALESCE(sc.generated_signals, 0) AS generated_signals,
  COALESCE(sc.signal_days, 0) AS signal_days,
  sc.last_signal_date,
  m.trades,
  m.expectancy_net_pct,
  m.profit_factor,
  m.max_drawdown_pct,
  m.robustness_score,
  CASE
    WHEN COALESCE(sc.generated_signals, 0) = 0 THEN 'sem_sinais'
    WHEN COALESCE(m.trades, 0) < 30 THEN 'amostra_insuficiente'
    WHEN m.expectancy_net_pct > 0 AND m.profit_factor >= 1.1 AND m.max_drawdown_pct >= -0.20 THEN 'promissora'
    WHEN m.expectancy_net_pct <= 0 OR m.profit_factor < 1 THEN 'reprovada'
    ELSE 'em_teste'
  END AS computed_status
FROM `ingestaokraken.cotacao_intraday.quant_baseline_strategy_config` AS c
LEFT JOIN signal_counts AS sc
  ON sc.strategy_id = c.strategy_id AND sc.strategy_version = c.strategy_version
LEFT JOIN metrics AS m
  ON m.strategy_id = c.strategy_id AND m.strategy_version = c.strategy_version;

CREATE OR REPLACE VIEW `ingestaokraken.cotacao_intraday.vw_quant_phase2_strategy_detail_alerts` AS
SELECT
  strategy_id,
  strategy_version,
  generated_signals,
  trades,
  expectancy_net_pct,
  profit_factor,
  max_drawdown_pct,
  ARRAY_CONCAT(
    IF(COALESCE(trades, 0) < 30, ['amostra_insuficiente'], []),
    IF(COALESCE(expectancy_net_pct, 0) <= 0, ['sem_expectativa_liquida_positiva'], []),
    IF(COALESCE(profit_factor, 0) < 1, ['profit_factor_fraco'], []),
    IF(COALESCE(max_drawdown_pct, 0) < -0.20, ['drawdown_elevado'], [])
  ) AS alerts
FROM `ingestaokraken.cotacao_intraday.vw_quant_phase2_baseline_status`;
