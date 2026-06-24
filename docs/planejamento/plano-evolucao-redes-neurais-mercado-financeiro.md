# Plano genérico de evolução de redes neurais para mercado financeiro

## Propósito

Este documento define um processo genérico, reutilizável e independente de uma rodada específica de treinamento para evoluir redes neurais aplicadas ao mercado financeiro. O plano serve para qualquer família de modelos usada em sinais, ranking, previsão de retorno, classificação de eventos, seleção de ativos ou gestão de risco.

O objetivo é transformar experimentos de machine learning em um ciclo governado de pesquisa, validação, comparação, promoção e monitoramento, reduzindo overfitting e priorizando resultado financeiro ajustado ao risco.

## Escopo

O plano cobre:

- modelos tabulares, sequenciais e híbridos;
- horizontes intraday, EOD, swing trade e carteiras rebalanceadas;
- tarefas de classificação, regressão, ranking e decisão multiobjetivo;
- treinamento offline, inferência agendada, paper trading e promoção controlada;
- comparação entre campeões e challengers;
- governança de dados, features, labels, métricas e decisões operacionais.

O plano não depende de um modelo, score, tela ou rodada atual. Qualquer análise específica deve entrar como anexo ou relatório de execução, nunca como regra central do processo.

## Princípios obrigatórios

1. **Objetivo econômico antes da métrica estatística**: a métrica principal deve representar utilidade financeira, não apenas acurácia, F1 ou loss.
2. **Validação temporal estrita**: treino, validação, teste e paper trading devem respeitar a ordem do tempo.
3. **Controle de vazamento de dados**: nenhuma feature, normalização ou label pode usar informação indisponível no momento da decisão.
4. **Comparação contra baselines**: todo modelo neural precisa superar alternativas simples, lineares ou heurísticas.
5. **Robustez antes de complexidade**: arquiteturas mais complexas só devem avançar se entregarem ganho líquido e estável.
6. **Promoção por estágios**: nenhum modelo sai de experimento para operação sem passar por gates explícitos.
7. **Rastreabilidade total**: dataset, features, labels, arquitetura, hiperparâmetros, código, métricas e decisão devem ser reproduzíveis.
8. **Gestão de risco integrada**: decisão, tamanho de posição, exposição e limites fazem parte do modelo operacional.

## Visão geral do ciclo de evolução

```text
Hipótese -> Dataset -> Labels -> Features -> Baselines -> Modelo neural
        -> Validação temporal -> Backtest com custos -> Robustez
        -> Paper trading -> Comitê/gate de promoção -> Monitoramento
        -> Retreino ou aposentadoria
```

Cada ciclo deve produzir evidências suficientes para responder:

- qual ineficiência ou padrão o modelo tenta capturar;
- por que uma rede neural é necessária;
- se o modelo supera baselines simples;
- se o resultado permanece fora da amostra;
- qual risco operacional e financeiro o modelo introduz;
- quando o modelo deve ser pausado, retreinado ou aposentado.

## Fase 0 — Formulação da hipótese

### Objetivo

Definir com precisão qual comportamento de mercado será explorado antes de treinar qualquer rede.

### Perguntas obrigatórias

- O modelo tenta capturar momentum, reversão, volatilidade, liquidez, ruptura, correlação, regime ou evento?
- O horizonte é intraday, D+1, vários dias, semanal ou mensal?
- A saída desejada é direção, retorno esperado, probabilidade de evento, ranking, alocação ou risco?
- Existe capacidade operacional para executar os sinais no preço assumido?
- Qual baseline simples deveria capturar parte da mesma hipótese?

### Entregáveis

- ficha da hipótese;
- universo de ativos;
- horizonte de decisão;
- regra de entrada/saída preliminar;
- baseline mínimo obrigatório;
- métrica financeira primária.

## Fase 1 — Governança do dataset

### Objetivo

Garantir que os dados usados para treinar, validar e operar sejam completos, auditáveis e temporalmente corretos.

### Ações

- Versionar snapshots ou queries de extração.
- Definir calendário de mercado e tratamento de feriados.
- Mapear corporate actions, splits, dividendos e mudanças de ticker.
- Medir cobertura por ativo, data e campo.
- Criar regras para outliers, buracos de cotação, volume zero e preços inválidos.
- Separar dados usados para pesquisa, backtest e operação.

### Checks mínimos

- ausência de datas futuras no treino;
- ausência de duplicidades por ativo/data/hora;
- consistência OHLCV;
- liquidez mínima;
- completude por janela;
- reprodutibilidade da extração.

## Fase 2 — Desenho de labels econômicos

### Objetivo

Criar alvos que representem o resultado financeiro esperado, e não apenas uma direção genérica do preço.

### Famílias de labels

- **Classificação direcional**: alta, queda ou neutro em um horizonte definido.
- **Regressão de retorno**: retorno futuro bruto ou líquido.
- **Evento de trade**: entrada tocada, alvo atingido, stop atingido, expiração.
- **Ranking cross-sectional**: quais ativos devem ficar no topo do universo.
- **Risco**: probabilidade de drawdown, gap adverso, stop ou alta volatilidade.
- **Multi-task**: combinação de direção, retorno, risco e probabilidade de execução.

### Regras

- O label deve refletir preço executável, custos e horizonte realista.
- Labels de classificação devem evitar classes artificiais quando a zona neutra é economicamente relevante.
- Labels de ranking devem ser avaliados por performance da carteira, não só por correlação ordinal.
- Labels devem ser versionados porque mudar o label muda o problema.

## Fase 3 — Engenharia de features

### Objetivo

Construir variáveis preditivas robustas, interpretáveis e disponíveis no momento da decisão.

### Blocos genéricos de features

- retornos em múltiplas janelas;
- volatilidade realizada e amplitude de candles;
- volume relativo e liquidez;
- distância para médias, máximas, mínimas e bandas;
- momentum e reversão à média;
- features de regime de mercado;
- correlação e beta contra benchmarks;
- fatores cross-sectional;
- features setoriais ou de cluster;
- features de calendário;
- features alternativas quando aprovadas e auditadas.

### Regras de normalização

- Normalizar usando somente estatísticas da janela de treino.
- Evitar estatísticas globais calculadas sobre todo o histórico.
- Preferir normalizações robustas a outliers quando houver caudas pesadas.
- Versionar transformações junto com o modelo.

## Fase 4 — Baselines obrigatórios

### Objetivo

Evitar que uma rede neural seja promovida quando uma regra simples entrega desempenho semelhante ou melhor.

### Baselines mínimos

- previsão aleatória com mesma frequência de sinais;
- buy and hold ou benchmark relevante;
- regra de momentum simples;
- regra de reversão simples;
- modelo linear/logístico;
- árvore ou gradient boosting simples, quando aplicável;
- ranking por retorno, volatilidade ou liquidez.

### Critério

A rede só deve avançar se superar os baselines em métricas financeiras e de robustez, depois de custos e fora da amostra.

## Fase 5 — Arquiteturas candidatas

### MLP tabular

Indicado para features agregadas e cross-sectional. Deve ser o primeiro baseline neural pela simplicidade, velocidade e facilidade de comparação.

### Ensemble neural

Combina modelos com seeds, janelas, subconjuntos de features ou arquiteturas diferentes. Deve ser usado para reduzir variância, desde que a diversidade seja real e mensurável.

### TCN, LSTM, GRU ou Transformer temporal

Indicado quando a sequência recente contém informação que features agregadas não capturam. Deve exigir amostra suficiente, regularização forte e validação walk-forward rigorosa.

### Modelos híbridos

Combinam ranking, classificação, regressão e camada de risco. São adequados quando a decisão final depende de múltiplos objetivos: retorno, probabilidade, liquidez e exposição.

### Modelos de incerteza

Incluem ensembles, dropout em inferência, quantile loss ou redes probabilísticas. São úteis para reduzir operação em cenários de baixa confiança.

## Fase 6 — Protocolo de treinamento

### Regras

- Usar splits temporais, nunca embaralhamento aleatório simples em séries temporais financeiras.
- Separar treino, validação, teste, holdout final e paper trading.
- Aplicar early stopping apenas na validação.
- Controlar seeds e registrar ambiente.
- Evitar tuning repetido no mesmo teste fora da amostra.
- Registrar todos os experimentos, inclusive os que falharam.

### Walk-forward

O protocolo padrão deve ser walk-forward:

1. treina em uma janela histórica;
2. valida na janela seguinte;
3. testa na janela posterior;
4. avança no tempo;
5. consolida métricas por fold;
6. analisa dispersão e pior caso, não apenas média.

## Fase 7 — Métricas de avaliação

### Métricas estatísticas

- loss de validação;
- acurácia balanceada;
- precision/recall por classe;
- AUC quando fizer sentido;
- calibração de probabilidade;
- erro médio absoluto ou quantílico para regressão.

### Métricas financeiras

- retorno líquido acumulado;
- retorno anualizado;
- Sharpe, Sortino e Calmar;
- drawdown máximo;
- profit factor;
- payoff médio;
- hit rate;
- turnover;
- exposição média;
- capacidade por liquidez;
- pior mês e pior sequência de perdas.

### Métricas de robustez

- estabilidade por janela walk-forward;
- estabilidade por ativo, setor e regime;
- sensibilidade a custos e slippage;
- degradação fora da amostra;
- concentração de resultado em poucos trades;
- correlação com modelos já ativos.

## Fase 8 — Score composto genérico

### Objetivo

Selecionar modelos por uma função multiobjetivo, evitando promoção baseada em uma única métrica.

```text
score_modelo =
  peso_retorno_risco      * retorno_ajustado_ao_risco
+ peso_robustez_temporal  * estabilidade_walk_forward
+ peso_drawdown           * controle_de_drawdown
+ peso_payoff             * qualidade_do_payoff
+ peso_capacidade         * capacidade_e_liquidez
+ peso_calibracao         * qualidade_da_calibracao
- penalidades
```

### Penalidades recomendadas

- poucos trades;
- alta concentração em poucos ativos;
- baixa liquidez;
- drawdown excessivo;
- instabilidade por regime;
- alta correlação com campeão atual;
- dependência de premissas frágeis de custo;
- complexidade sem ganho material.

Os pesos devem ser configuráveis por estratégia e aprovados antes da seleção de modelos.

## Fase 9 — Backtest realista

### Premissas obrigatórias

- custos transacionais;
- slippage;
- spread;
- liquidez máxima negociável;
- latência da decisão;
- preço realmente executável;
- limites de exposição;
- eventos sem execução;
- tratamento de gaps;
- restrições de venda, aluguel ou short quando aplicável.

### Resultado esperado

O backtest deve produzir trades, métricas agregadas, métricas por regime, auditoria de execução e comparação contra baselines.

## Fase 10 — Calibração, thresholds e sizing

### Calibração

Modelos que emitem probabilidades devem ser calibrados. Probabilidade mal calibrada pode gerar sizing incorreto mesmo quando o ranking parece bom.

### Thresholds

- Definir zonas de operação e não operação.
- Ajustar thresholds por custo, volatilidade e regime.
- Evitar operar quando a vantagem esperada não supera custos e incerteza.

### Sizing

- Definir tamanho por confiança, risco ou volatilidade.
- Impor teto por ativo, setor, estratégia e carteira.
- Reduzir exposição em regime adverso ou baixa confiança.

## Fase 11 — Paper trading

### Objetivo

Validar o modelo em ambiente operacional sem risco financeiro real, medindo diferença entre expectativa de backtest e execução simulada ao vivo.

### Métricas

- sinais gerados;
- sinais filtrados;
- trades executáveis;
- retorno líquido simulado;
- drawdown;
- slippage estimado;
- divergência contra backtest;
- drift de dados e features;
- estabilidade de calibração;
- disponibilidade operacional.

### Gate de saída

Um modelo só pode avançar se mantiver desempenho consistente por uma janela mínima definida, com quantidade suficiente de sinais e sem violações de risco.

## Fase 12 — Promoção, operação e monitoramento

### Estados sugeridos

- `research`: hipótese em estudo;
- `trained`: modelo treinado e registrado;
- `validated`: passou em validação temporal;
- `backtest_candidate`: passou para backtest realista;
- `paper_trade`: está em simulação operacional;
- `production_candidate`: aprovado para operação controlada;
- `active`: modelo ativo;
- `paused`: pausado por risco, drift ou falha;
- `retired`: aposentado.

### Monitoramento contínuo

- performance realizada contra esperada;
- drawdown e risco agregado;
- drift de features;
- drift de labels;
- saúde da inferência;
- latência e falhas de pipeline;
- concentração de exposição;
- mudança de regime.

## Fase 13 — Retreino e aposentadoria

### Retreino

O retreino deve ocorrer por agenda, por evento ou por degradação estatística. Todo retreino deve competir contra o campeão vigente e contra baselines.

### Aposentadoria

Um modelo deve ser aposentado quando:

- perde vantagem estatística ou econômica;
- viola limites de drawdown;
- degrada em paper ou produção;
- depende de dados que deixaram de existir;
- é substituído por modelo mais simples e equivalente;
- apresenta risco operacional excessivo.

## Roadmap genérico de implantação

### Etapa 1 — Fundação

- Definir contrato de experimentos.
- Versionar datasets, labels e features.
- Criar baselines obrigatórios.
- Criar métricas financeiras padrão.

### Etapa 2 — Laboratório neural

- Treinar MLP tabular baseline.
- Treinar modelos lineares e não neurais comparativos.
- Implementar walk-forward.
- Registrar experimentos e artefatos.

### Etapa 3 — Seleção robusta

- Implementar score composto configurável.
- Adicionar análise por regime, ativo e liquidez.
- Implementar penalidades de concentração e overfitting.
- Criar ranking de campeões e challengers.

### Etapa 4 — Simulação operacional

- Rodar backtest realista.
- Ativar paper trading.
- Monitorar divergência entre esperado e realizado.
- Definir gates de promoção.

### Etapa 5 — Operação controlada

- Promover apenas modelos aprovados.
- Aplicar limites de risco.
- Monitorar drift e performance.
- Retreinar ou aposentar conforme regras.

## Como usar este plano em uma situação específica

Para aplicar o plano a uma rodada, modelo ou painel específico, crie um relatório separado contendo:

- data da análise;
- modelos avaliados;
- dataset e período;
- métricas observadas;
- hipóteses levantadas;
- comandos ou consultas usados na validação;
- decisão tomada;
- próximos passos.

Esse relatório específico deve referenciar este plano genérico, mas não substituir suas regras centrais.
