# Fase 5 — Validação estatística e robustez

## Objetivo executado

Esta etapa prepara a camada que separa estratégias possivelmente superajustadas daquelas com evidência mínima de estabilidade estatística. A implementação cria políticas versionadas, cortes fora da amostra, janelas walk-forward, testes por subperíodos/grupos de ativos, painéis de custos estressados e comparação contra aleatorização para alimentar a tela **Validação e Robustez**.

## Artefato criado

- Script BigQuery: `infra/bq/12_quant_phase5_statistical_robustness.sql`.

## Componentes técnicos

### `quant_validation_policy_config`

Tabela de política versionada para calibrar validação e robustez:

- proporção treino/validação/teste;
- tamanho e passo de walk-forward;
- amostra mínima por split e subperíodo;
- degradação máxima fora da amostra;
- multiplicadores de custo e slippage estressados;
- score mínimo de robustez.

A versão inicial é `statistical_robustness_v1`/`v1`, com status `em_teste`.

### `vw_quant_phase5_oos_splits`

View de classificação de cada trade em `treino`, `validacao` ou `teste`, preservando:

- identificadores de estratégia e versão;
- ticker, lado e data de referência;
- PnL líquido, custos, slippage e outcome;
- sequência temporal do trade e total de trades da estratégia.

### `vw_quant_phase5_oos_summary`

View consolidada para os cards principais da tela:

- resultado em treino;
- resultado em validação;
- resultado em teste;
- degradação fora da amostra;
- profit factor por split;
- status OOS (`aprovado_oos`, `falha_fora_da_amostra`, `degradacao_excessiva` ou `amostra_insuficiente`).

### `vw_quant_phase5_walk_forward`

View mensal para gráfico de walk-forward:

- trades por janela;
- expectancy líquida;
- profit factor;
- win rate;
- média móvel de expectancy em seis janelas;
- quantidade de janelas positivas recentes.

### `vw_quant_phase5_subperiod_asset_group_tests`

View para testar estabilidade por recortes independentes:

- subperíodos mensais;
- quintis de grupos de ativos;
- trades, expectancy, PnL total e profit factor por bucket.

### `vw_quant_phase5_cost_stress`

View para o painel de custos:

- resultado sem custo;
- resultado com custo normal;
- custo ampliado;
- slippage ampliado;
- custo e slippage ampliados simultaneamente;
- status de sobrevivência a custos.

### `vw_quant_phase5_randomization_benchmark`

View de comparação contra aleatorização usando o universo de trades disponíveis na mesma data:

- expectancy da estratégia;
- expectancy média do universo aleatório por dia;
- excesso de expectancy contra o benchmark;
- percentual de dias acima do benchmark;
- status de superação da aleatorização.

### `vw_quant_phase5_parameter_sensitivity`

View inicial para o heatmap de parâmetros. Ela expõe o JSON de parâmetros das baselines e métricas recentes, marcando estratégias como:

- `parametros_estaveis`;
- `candidato_a_grade_parametros`;
- `parametros_fragil`;
- `amostra_insuficiente`.

### `vw_quant_phase5_robustness_dashboard`

View agregadora para a tela **Validação e Robustez**:

- cards de treino, validação e teste;
- degradação fora da amostra;
- percentual de janelas walk-forward positivas;
- resultado com custos estressados;
- comparação contra aleatorização;
- score de robustez de 0 a 100;
- alertas de overfitting.

## Decisões de implementação

- O split fora da amostra é temporal e por sequência de trades, evitando embaralhar dados de mercado.
- A política inicial usa 60% treino, 20% validação e 20% teste para manter amostra em todas as etapas.
- O walk-forward foi materializado mensalmente para oferecer visualização estável e simples na primeira versão da tela.
- O teste contra aleatorização compara a estratégia com o universo de trades no mesmo dia, reduzindo distorções por regime de mercado.
- A sensibilidade a parâmetros começa como uma view de exposição e diagnóstico; grades densas de parâmetros podem ser adicionadas quando houver execuções versionadas suficientes.
- O score de robustez combina quatro pilares: OOS, walk-forward, custos estressados e benchmark aleatório.

## Critérios de saída atendidos

- Há validação fora da amostra com treino, validação e teste.
- Há análise walk-forward por janelas mensais.
- Há testes por subperíodos e grupos de ativos.
- Há teste de sobrevivência com custos e slippage ampliados.
- Há comparação contra aleatorização.
- Há alertas explícitos de overfitting e score consolidado de robustez.

## Próximos passos

1. Aplicar `infra/bq/12_quant_phase5_statistical_robustness.sql` no BigQuery.
2. Validar a distribuição de trades por split e ajustar amostras mínimas conforme histórico real.
3. Expor endpoints backend para `vw_quant_phase5_robustness_dashboard`, `vw_quant_phase5_walk_forward`, `vw_quant_phase5_cost_stress` e `vw_quant_phase5_parameter_sensitivity`.
4. Criar a tela **Validação e Robustez** no frontend.
5. Evoluir a sensibilidade de parâmetros para matrizes completas quando houver execuções de backtest por grade/versionamento.
