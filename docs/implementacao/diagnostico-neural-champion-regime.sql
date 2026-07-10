-- Diagnóstico pós-Fase 4 TCN bt3+ca: champion activity, trades e regimes.
-- Objetivo: entender por que `require_champion_activity=true` zerou trades e
-- transformar o próximo treino em hipótese estrutural de features/labels/regime,
-- não em nova blocklist manual.
--
-- Ajuste os DECLAREs abaixo se mudar snapshot/família.

DECLARE p_dataset_snapshot STRING DEFAULT 'neural_eod_training_dataset_2026-06-27_champion_v1';
DECLARE p_bt_family_hash STRING DEFAULT 'neural_eod_phase4_tcn_sequence_p50_m08_t20_d15_l20_bt3_onco3_brkm5_csan3_v1';
DECLARE p_bt_ca_family_hash STRING DEFAULT 'neural_eod_phase4_tcn_sequence_p50_m08_t20_d15_l20_bt3_ca_v2';

-- 1) Sanidade do snapshot com champion materializado.
SELECT
  dataset_snapshot,
  COUNT(*) AS rows_count,
  COUNTIF(champion_trade_active) AS champion_active_rows,
  COUNTIF(champion_net_return IS NOT NULL) AS champion_return_rows,
  COUNT(DISTINCT champion_strategy_id) AS champion_strategy_ids,
  MIN(reference_date) AS min_reference_date,
  MAX(reference_date) AS max_reference_date
FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
WHERE dataset_snapshot = p_dataset_snapshot
GROUP BY dataset_snapshot;

-- 2) Sobreposição da TCN bt3 sem CA contra atividade real do champion.
-- Se a maioria dos trades estiver em champion_trade_active=false, o filtro CA tende
-- a remover cobertura; se os poucos overlaps forem bons, a próxima hipótese deve
-- ampliar contexto/regime do champion em vez de exigir igualdade estrita.
WITH bt AS (
  SELECT
    ticker,
    reference_date,
    fold_id,
    seed,
    trades,
    exposure,
    model_net_return,
    champion_net_return,
    delta_net_return
  FROM `ingestaokraken.cotacao_intraday.neural_daily_returns`
  WHERE candidate_family_hash = p_bt_family_hash
    AND trades > 0
), ds AS (
  SELECT
    ticker,
    reference_date,
    champion_trade_active,
    champion_net_return AS dataset_champion_net_return,
    label_class,
    volatility_20d,
    financial_volume_z20,
    volume_ratio_20d,
    return_5d,
    log_return_5d
  FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
  WHERE dataset_snapshot = p_dataset_snapshot
)
SELECT
  COUNT(*) AS traded_daily_rows,
  COUNTIF(ds.champion_trade_active) AS overlap_champion_active_rows,
  COUNTIF(NOT COALESCE(ds.champion_trade_active, FALSE)) AS against_champion_neutral_rows,
  SUM(bt.trades) AS total_trade_markers,
  SUM(IF(ds.champion_trade_active, bt.trades, 0)) AS trades_when_champion_active,
  SUM(IF(NOT COALESCE(ds.champion_trade_active, FALSE), bt.trades, 0)) AS trades_when_champion_neutral,
  AVG(bt.delta_net_return) AS avg_delta,
  AVG(IF(ds.champion_trade_active, bt.delta_net_return, NULL)) AS avg_delta_champion_active,
  AVG(IF(NOT COALESCE(ds.champion_trade_active, FALSE), bt.delta_net_return, NULL)) AS avg_delta_champion_neutral,
  MIN(bt.delta_net_return) AS worst_delta
FROM bt
LEFT JOIN ds USING (ticker, reference_date);

-- 3) Regime/features das linhas em que a TCN bt3 operou, separado por champion ativo/neutro.
WITH bt AS (
  SELECT ticker, reference_date, fold_id, seed, trades, exposure, model_net_return, champion_net_return, delta_net_return
  FROM `ingestaokraken.cotacao_intraday.neural_daily_returns`
  WHERE candidate_family_hash = p_bt_family_hash
    AND trades > 0
), ds AS (
  SELECT ticker, reference_date, champion_trade_active, label_class, volatility_20d,
         financial_volume_z20, volume_ratio_20d, return_5d, log_return_5d
  FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
  WHERE dataset_snapshot = p_dataset_snapshot
)
SELECT
  COALESCE(CAST(ds.champion_trade_active AS STRING), 'missing') AS champion_active,
  COUNT(*) AS rows_count,
  SUM(bt.trades) AS trades,
  AVG(bt.delta_net_return) AS avg_delta,
  MIN(bt.delta_net_return) AS worst_delta,
  AVG(ds.volatility_20d) AS avg_volatility_20d,
  AVG(ds.financial_volume_z20) AS avg_financial_volume_z20,
  AVG(ds.volume_ratio_20d) AS avg_volume_ratio_20d,
  AVG(ds.return_5d) AS avg_return_5d,
  AVG(ds.log_return_5d) AS avg_log_return_5d
FROM bt
LEFT JOIN ds USING (ticker, reference_date)
GROUP BY champion_active
ORDER BY champion_active;

-- 4) Piores linhas da TCN bt3 para diagnóstico de ticker/data/fold/regime.
WITH bt AS (
  SELECT ticker, reference_date, fold_id, seed, trades, exposure, model_net_return, champion_net_return, delta_net_return
  FROM `ingestaokraken.cotacao_intraday.neural_daily_returns`
  WHERE candidate_family_hash = p_bt_family_hash
), ds AS (
  SELECT ticker, reference_date, champion_trade_active, label_class, volatility_20d,
         financial_volume_z20, volume_ratio_20d, return_5d, log_return_5d
  FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`
  WHERE dataset_snapshot = p_dataset_snapshot
)
SELECT
  bt.ticker,
  bt.reference_date,
  bt.fold_id,
  bt.seed,
  bt.trades,
  bt.exposure,
  ds.champion_trade_active,
  ds.label_class,
  bt.model_net_return,
  bt.champion_net_return,
  bt.delta_net_return,
  ds.volatility_20d,
  ds.financial_volume_z20,
  ds.volume_ratio_20d,
  ds.return_5d,
  ds.log_return_5d
FROM bt
LEFT JOIN ds USING (ticker, reference_date)
ORDER BY bt.delta_net_return ASC, bt.reference_date ASC
LIMIT 50;

-- 5) Confirmação da rodada bt3+ca: deve mostrar rejeição por trades zerados.
SELECT
  candidate_family_hash,
  decision_status,
  failed_criteria,
  metrics_json.seeds AS seeds,
  metrics_json.total_trades AS total_trades,
  metrics_json.positive_folds AS positive_folds,
  metrics_json.median_delta_expectancy_vs_champion AS median_delta,
  metrics_json.worst_fold_delta_expectancy_vs_champion AS worst_delta,
  metrics_json.max_drawdown AS max_drawdown,
  metrics_json.stable_across_seeds AS stable_across_seeds,
  decided_at
FROM `ingestaokraken.cotacao_intraday.neural_gate_decisions`
WHERE candidate_family_hash = p_bt_ca_family_hash
ORDER BY decided_at DESC
LIMIT 5;
