# Fase 0 — Preparação e inventário dos dados quantitativos

## Objetivo executado

Esta etapa materializa o inventário inicial dos dados usados pelos novos sistemas quantitativos e define consultas padronizadas para as telas **Inventário de Dados** e **Qualidade dos Dados**.

## Fonte e método

- Acesso ao MCP Server via JSON-RPC em `http://mcpserversisacao.shop/mcp`.
- Consulta de metadados no BigQuery em `ingestaokraken.cotacao_intraday.INFORMATION_SCHEMA`.
- Consulta de métricas agregadas nas tabelas canônicas de cotações diária e intraday.
- Criação do script `infra/bq/07_quant_phase0_inventory.sql` com views operacionais somente leitura.

## Tabelas inventariadas para a Fase 0

| Área | Tabela/View | Uso na esteira quantitativa |
|---|---|---|
| Universo de ativos | `acao_bovespa` | Cadastro de tickers e flag de ativo/inativo. |
| Feriados/calendário | `feriados_b3` | Cálculo de dias úteis esperados de pregão. |
| Cotação diária | `cotacao_ohlcv_diario` | Base principal para baselines, ranking, backtests EOD e qualidade diária. |
| Cotação intraday bruta | `cotacao_b3` | Base para estudos intraday, recência de coleta e qualidade de preços intraday. |
| Cotação intraday operacional | `cotacao_bovespa` | Tabela histórica/operacional já usada por monitoramentos legados. |
| Candles intraday agregados | `candles_intraday_15m`, `candles_intraday_1h` | Granularidades candidatas para estratégias por horário. |
| Sinais | `sinais_eod` | Histórico de sinais existentes para comparação com novos sistemas. |
| Backtests | `backtest_trades`, `backtest_metrics` | Referência de resultados atuais e alvo de padronização na Fase 1. |
| Qualidade | `dq_checks_daily`, `dq_incidents` | Auditoria existente de checks e incidentes. |
| Configuração | `pipeline_config`, `parametros_estrategia` | Parâmetros operacionais e versões de estratégia. |
| Operacional | `vw_pipeline_status`, `mv_indicadores` | Views já existentes para status e indicadores técnicos. |

## Leitura inicial do ambiente BigQuery em 2026-06-14

| Item | Resultado observado |
|---|---:|
| Tabelas/views no dataset `cotacao_intraday` | 38 |
| Tickers na cotação diária `cotacao_ohlcv_diario` | 152 |
| Período diário observado | 2026-02-27 a 2026-06-12 |
| Candles diários observados | 11.040 |
| Preços diários zerados/inválidos na leitura agregada | 0 |
| Volumes diários zerados/inválidos na leitura agregada | 0 |
| Tickers na cotação intraday bruta `cotacao_b3` | 50 |
| Período intraday bruto observado | 2026-02-26 a 2026-06-12 |
| Registros intraday brutos observados | 57.797 |
| Preços intraday zerados/inválidos na leitura agregada | 0 |

## Views criadas para as telas da Fase 0

### `vw_quant_data_inventory_summary`

Alimenta os cards de resumo da tela **Inventário de Dados**:

- quantidade de tickers ativos e totais;
- tickers cobertos nas bases diária e intraday;
- primeira e última data disponível;
- total de candles diários e intraday;
- percentual agregado de dados válidos;
- última atualização observada.

### `vw_quant_ticker_coverage`

Alimenta a tabela de cobertura por ticker:

- primeira e última data;
- dias com dados;
- dias esperados por calendário B3 simplificado;
- percentual de cobertura;
- volume financeiro médio;
- contadores de preços inválidos, volumes inválidos e duplicidades;
- status de elegibilidade.

Regra inicial de elegibilidade:

1. ticker ativo no cadastro;
2. cobertura diária mínima de 90%;
3. volume financeiro médio mínimo de R$ 1.000.000;
4. zero dias com preço inválido;
5. zero dias com volume inválido;
6. zero duplicidades por ticker/data.

Tickers com cobertura diária mínima de 75%, mas que ainda não atendem todos os critérios, ficam em `observacao`. Os demais ficam em `excluir`.

### `vw_quant_data_quality_incidents`

Alimenta a tela **Qualidade dos Dados** com incidentes derivados diretamente das cotações:

- OHLC diário inválido;
- volume diário ausente ou zerado;
- duplicidade diária por ticker/data;
- preço intraday ausente ou zerado.

## Lacunas e pontos de atenção

- A cobertura intraday bruta tem universo menor que a base diária: 50 tickers contra 152 tickers observados na base diária.
- O inventário de setor ainda não foi identificado nas tabelas canônicas; os filtros por setor da tela devem ficar opcionais até haver uma fonte confiável.
- A Fase 0 cria regras iniciais objetivas, mas os limiares de liquidez e cobertura devem permanecer parametrizáveis na Fase 1.
- As views usam calendário B3 simplificado por dias úteis e feriados cadastrados; qualquer ausência no cadastro `feriados_b3` impacta o cálculo de dias esperados.

## Critérios de saída

- Inventário de tabelas BigQuery documentado.
- Views operacionais definidas para resumo, cobertura por ticker e incidentes de qualidade.
- Regras iniciais de exclusão e elegibilidade documentadas.
- Base mínima preparada para a Fase 1: motor comum de backtest e métricas.
