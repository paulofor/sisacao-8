-- Cria a tabela de feriados da B3 usada para bloquear coletas em dias sem pregão.
-- Ajuste o projeto/dataset conforme necessário antes de executar.

CREATE SCHEMA IF NOT EXISTS `ingestaokraken.cotacao_intraday`;

CREATE TABLE IF NOT EXISTS `ingestaokraken.cotacao_intraday.feriados_b3`
(
  data_feriado DATE NOT NULL,
  nome_feriado STRING NOT NULL,
  mercado STRING NOT NULL,
  ativo BOOL NOT NULL,
  atualizado_em DATETIME NOT NULL
)
PARTITION BY data_feriado
OPTIONS (
  description = "Calendário de feriados da B3 para controle de execução dos coletores"
);

MERGE `ingestaokraken.cotacao_intraday.feriados_b3` target
USING (
  SELECT DATE '2026-01-01' AS data_feriado, 'Confraternização Universal' AS nome_feriado
  UNION ALL SELECT DATE '2026-02-16', 'Carnaval'
  UNION ALL SELECT DATE '2026-02-17', 'Carnaval'
  UNION ALL SELECT DATE '2026-04-03', 'Sexta-feira Santa'
  UNION ALL SELECT DATE '2026-04-21', 'Tiradentes'
  UNION ALL SELECT DATE '2026-05-01', 'Dia do Trabalho'
  UNION ALL SELECT DATE '2026-06-04', 'Corpus Christi'
  UNION ALL SELECT DATE '2026-09-07', 'Independência do Brasil'
  UNION ALL SELECT DATE '2026-10-12', 'Nossa Senhora Aparecida'
  UNION ALL SELECT DATE '2026-11-02', 'Finados'
  UNION ALL SELECT DATE '2026-11-15', 'Proclamação da República'
  UNION ALL SELECT DATE '2026-12-25', 'Natal'
) source
ON target.data_feriado = source.data_feriado
  AND target.mercado = 'B3'
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
