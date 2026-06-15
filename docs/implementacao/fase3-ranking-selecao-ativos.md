# Fase 3 — Ranking e seleção de ativos

## Objetivo executado

Esta etapa prepara a evolução de sinais isolados para um modelo diário de ranking relativo. O objetivo é ordenar o universo elegível de ativos por score composto, selecionar carteiras top N e medir se os ativos mais bem ranqueados realmente apresentam desempenho futuro superior aos demais.

## Artefato criado

- Script BigQuery: `infra/bq/10_quant_phase3_asset_ranking.sql`.

O script cria a configuração versionada dos rankings e views para alimentar as telas **Ranking Diário de Oportunidades** e **Performance do Ranking**.

## Componentes técnicos

### `quant_ranking_model_config`

Tabela de configuração com dois modelos iniciais:

| Modelo | Descrição | Top N avaliados |
|---|---|---|
| `asset_ranking_simple_v1` | Score simples por força relativa, momentum curto, volume relativo e qualidade do candle. | 3, 5 e 10 |
| `asset_ranking_weighted_v1` | Score ponderado com força relativa, momentum, volume, volatilidade controlada, distância da média, candle e regime do índice. | 3, 5 e 10 |

A tabela permite versionar pesos, horizonte de manutenção, frequência de rebalanceamento, liquidez mínima e status operacional.

### `vw_quant_phase3_ranking_factors`

View de fatores diários sobre o universo elegível:

- força relativa de 20 pregões;
- momentum curto de 5 pregões;
- volume relativo de 20 pregões;
- volatilidade realizada de 20 pregões;
- distância percentual da média de 20 pregões;
- qualidade do candle via localização do fechamento dentro da amplitude;
- regime agregado do mercado por amplitude e retorno médio;
- retorno futuro de 5 pregões para avaliação posterior do ranking.

### `vw_quant_phase3_daily_asset_ranking`

View principal do ranking diário:

- posição do ativo no ranking;
- decil do score;
- score final e decomposição dos fatores em JSON;
- preço atual, liquidez e risco estimado;
- regime de mercado;
- sugestão operacional (`operar`, `observar` ou `evitar`);
- selo de confiança (`alta`, `media` ou `baixa`).

### `vw_quant_phase3_top_n_portfolios`

View de carteiras top N para backtest comparável:

- top 3;
- top 5;
- top 10;
- ativos selecionados por data;
- retorno futuro médio de 5 pregões;
- risco médio estimado.

### `vw_quant_phase3_ranking_performance`

View de performance agregada para medir qualidade do ranking:

- retorno médio das carteiras top N;
- volatilidade do retorno top N;
- taxa de dias positivos;
- excesso de retorno contra seleção aleatória;
- correlação entre decil e retorno futuro;
- spread entre primeiro e último decil;
- status calculado (`amostra_insuficiente`, `monotonicidade_promissora`, `sem_monotonicidade` ou `em_observacao`).

## Decisões de implementação

- A Fase 3 reutiliza `vw_quant_phase2_daily_features` para evitar duplicar cálculo de retornos, médias e volume relativo.
- O ranking só considera ativos com volume financeiro mínimo de R$ 1 milhão, herdando a disciplina de elegibilidade da Fase 0.
- A avaliação inicial usa retorno futuro de 5 pregões, alinhado ao horizonte de várias baselines da Fase 2.
- A seleção top N é feita em view, sem persistência automática de ordens ou trades.
- O benchmark de seleção aleatória é aproximado pela média diária do universo ranqueado, servindo como referência simples antes de simulações mais sofisticadas.
- O critério de monotonicidade usa correlação entre decil e retorno futuro, além do spread entre primeiro e último decil.

## Critérios de saída atendidos

- Há um score composto com os fatores exigidos no plano.
- Existem seleções top 3, top 5 e top 10 por data.
- O script compara ranking simples e ranking ponderado por configuração versionada.
- A performance permite verificar monotonicidade por decil e excesso contra seleção aleatória.

## Próximos passos

1. Aplicar `infra/bq/10_quant_phase3_asset_ranking.sql` no BigQuery.
2. Validar a distribuição dos scores e calibrar pesos com base em monotonicidade, não apenas retorno agregado.
3. Inserir seleções top N promissoras em `quant_strategy_signals` para backtest completo no motor comum.
4. Expor endpoints backend para `vw_quant_phase3_daily_asset_ranking` e `vw_quant_phase3_ranking_performance`.
5. Criar as telas **Ranking Diário de Oportunidades** e **Performance do Ranking** no frontend.
