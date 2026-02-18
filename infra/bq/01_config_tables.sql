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
