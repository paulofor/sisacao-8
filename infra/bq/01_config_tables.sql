-- Tabelas de configuração (tickers, parâmetros e feriados da B3).

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.acao_bovespa`
(
  ticker STRING NOT NULL,
  nome STRING,
  segmento STRING,
  ativo BOOL NOT NULL DEFAULT TRUE,
  origem STRING,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING
)
PARTITION BY DATE(updated_at)
CLUSTER BY ativo, segmento
OPTIONS (
  description = "Tickers monitorados pelo Sisacao-8"
);

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.parametros_estrategia`
(
  parametro_id STRING NOT NULL,
  estrategia STRING DEFAULT 'signals_eod',
  x_pct FLOAT64 NOT NULL,
  target_pct FLOAT64 NOT NULL,
  stop_pct FLOAT64 NOT NULL,
  horizon_days INT64 NOT NULL,
  allow_sell BOOL DEFAULT TRUE,
  max_signals INT64 NOT NULL DEFAULT 5,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING
)
PARTITION BY DATE(updated_at)
OPTIONS (
  description = "Parâmetros versionados das estratégias de sinais"
);

MERGE `@@PROJECT_ID@@.cotacao_intraday.parametros_estrategia` target
USING (
  SELECT
    'signals_v1' AS parametro_id,
    'signals_eod' AS estrategia,
    0.02 AS x_pct,
    0.07 AS target_pct,
    0.07 AS stop_pct,
    10 AS horizon_days,
    TRUE AS allow_sell,
    5 AS max_signals,
    'seed' AS updated_by
) source
ON target.parametro_id = source.parametro_id
WHEN MATCHED THEN
  UPDATE SET
    x_pct = source.x_pct,
    target_pct = source.target_pct,
    stop_pct = source.stop_pct,
    horizon_days = source.horizon_days,
    allow_sell = source.allow_sell,
    max_signals = source.max_signals,
    estrategia = source.estrategia,
    updated_at = CURRENT_TIMESTAMP(),
    updated_by = source.updated_by
WHEN NOT MATCHED THEN
  INSERT (
    parametro_id,
    estrategia,
    x_pct,
    target_pct,
    stop_pct,
    horizon_days,
    allow_sell,
    max_signals,
    updated_by
  )
  VALUES (
    source.parametro_id,
    source.estrategia,
    source.x_pct,
    source.target_pct,
    source.stop_pct,
    source.horizon_days,
    source.allow_sell,
    source.max_signals,
    source.updated_by
  );

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.pipeline_config`
(
  config_id STRING NOT NULL,
  config_version STRING NOT NULL,
  daily_min_coverage FLOAT64 NOT NULL,
  intraday_min_coverage FLOAT64 NOT NULL,
  intraday_latest_time TIME NOT NULL,
  intraday_duplicate_tolerance INT64 NOT NULL DEFAULT 0,
  intraday_max_staleness_minutes INT64 NOT NULL DEFAULT 45,
  signals_deadline TIME NOT NULL,
  signals_grace_minutes INT64 NOT NULL DEFAULT 60,
  backtest_deadline TIME NOT NULL,
  backtest_grace_minutes INT64 NOT NULL DEFAULT 60,
  allow_offline_fallback BOOL NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
PARTITION BY DATE(created_at)
OPTIONS (
  description = "Configurações operacionais versionadas do pipeline"
);

MERGE `@@PROJECT_ID@@.cotacao_intraday.pipeline_config` target
USING (
  SELECT
    'default' AS config_id,
    'pipelines_v1' AS config_version,
    0.9 AS daily_min_coverage,
    0.7 AS intraday_min_coverage,
    TIME '17:45:00' AS intraday_latest_time,
    0 AS intraday_duplicate_tolerance,
    45 AS intraday_max_staleness_minutes,
    TIME '22:00:00' AS signals_deadline,
    60 AS signals_grace_minutes,
    TIME '23:00:00' AS backtest_deadline,
    60 AS backtest_grace_minutes,
    FALSE AS allow_offline_fallback,
    'seed' AS created_by
) source
ON target.config_id = source.config_id AND target.config_version = source.config_version
WHEN MATCHED THEN
  UPDATE SET
    daily_min_coverage = source.daily_min_coverage,
    intraday_min_coverage = source.intraday_min_coverage,
    intraday_latest_time = source.intraday_latest_time,
    intraday_duplicate_tolerance = source.intraday_duplicate_tolerance,
    intraday_max_staleness_minutes = source.intraday_max_staleness_minutes,
    signals_deadline = source.signals_deadline,
    signals_grace_minutes = source.signals_grace_minutes,
    backtest_deadline = source.backtest_deadline,
    backtest_grace_minutes = source.backtest_grace_minutes,
    allow_offline_fallback = source.allow_offline_fallback,
    created_at = CURRENT_TIMESTAMP(),
    created_by = source.created_by
WHEN NOT MATCHED THEN
  INSERT (
    config_id,
    config_version,
    daily_min_coverage,
    intraday_min_coverage,
    intraday_latest_time,
    intraday_duplicate_tolerance,
    intraday_max_staleness_minutes,
    signals_deadline,
    signals_grace_minutes,
    backtest_deadline,
    backtest_grace_minutes,
    allow_offline_fallback,
    created_by
  )
  VALUES (
    source.config_id,
    source.config_version,
    source.daily_min_coverage,
    source.intraday_min_coverage,
    source.intraday_latest_time,
    source.intraday_duplicate_tolerance,
    source.intraday_max_staleness_minutes,
    source.signals_deadline,
    source.signals_grace_minutes,
    source.backtest_deadline,
    source.backtest_grace_minutes,
    source.allow_offline_fallback,
    source.created_by
  );

CREATE TABLE IF NOT EXISTS `@@PROJECT_ID@@.cotacao_intraday.feriados_b3`
(
  data_feriado DATE NOT NULL,
  nome_feriado STRING NOT NULL,
  mercado STRING NOT NULL,
  ativo BOOL NOT NULL,
  atualizado_em DATETIME NOT NULL
)
PARTITION BY data_feriado
OPTIONS (
  description = "Calendário oficial da B3 utilizado para pausar os jobs"
);

MERGE `@@PROJECT_ID@@.cotacao_intraday.feriados_b3` target
USING (
  SELECT DATE '2026-01-01' AS data_feriado, 'Confraternização Universal' AS nome_feriado UNION ALL
  SELECT DATE '2026-02-16', 'Carnaval' UNION ALL
  SELECT DATE '2026-02-17', 'Carnaval' UNION ALL
  SELECT DATE '2026-04-03', 'Sexta-feira Santa' UNION ALL
  SELECT DATE '2026-04-21', 'Tiradentes' UNION ALL
  SELECT DATE '2026-05-01', 'Dia do Trabalho' UNION ALL
  SELECT DATE '2026-06-04', 'Corpus Christi' UNION ALL
  SELECT DATE '2026-09-07', 'Independência do Brasil' UNION ALL
  SELECT DATE '2026-10-12', 'Nossa Senhora Aparecida' UNION ALL
  SELECT DATE '2026-11-02', 'Finados' UNION ALL
  SELECT DATE '2026-11-15', 'Proclamação da República' UNION ALL
  SELECT DATE '2026-12-25', 'Natal' UNION ALL
  SELECT DATE '2027-01-01', 'Confraternização Universal' UNION ALL
  SELECT DATE '2027-02-08', 'Carnaval' UNION ALL
  SELECT DATE '2027-02-09', 'Carnaval' UNION ALL
  SELECT DATE '2027-03-26', 'Sexta-feira Santa' UNION ALL
  SELECT DATE '2027-04-21', 'Tiradentes' UNION ALL
  SELECT DATE '2027-06-03', 'Corpus Christi' UNION ALL
  SELECT DATE '2027-09-07', 'Independência do Brasil' UNION ALL
  SELECT DATE '2027-10-12', 'Nossa Senhora Aparecida' UNION ALL
  SELECT DATE '2027-11-02', 'Finados' UNION ALL
  SELECT DATE '2027-11-15', 'Proclamação da República' UNION ALL
  SELECT DATE '2027-12-24', 'Véspera de Natal' UNION ALL
  SELECT DATE '2027-12-31', 'Véspera de Ano Novo'
) source
ON target.data_feriado = source.data_feriado AND target.mercado = 'B3'
WHEN MATCHED THEN
  UPDATE SET
    nome_feriado = source.nome_feriado,
    ativo = TRUE,
    atualizado_em = CURRENT_DATETIME('America/Sao_Paulo')
WHEN NOT MATCHED THEN
  INSERT (data_feriado, nome_feriado, mercado, ativo, atualizado_em)
  VALUES (
    source.data_feriado,
    source.nome_feriado,
    'B3',
    TRUE,
    CURRENT_DATETIME('America/Sao_Paulo')
  );
