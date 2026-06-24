# Plano de evolução das redes neurais para mercado financeiro

## Contexto e diagnóstico

O painel operacional mostra múltiplas variantes `neural_eod_mlp` em estado `keep_candidate`, com score aproximado entre `0,407` e `0,427`, precisão direcional visível entre `35%` e `40,8%`, cobertura entre `61,5%` e `88,7%`, generalização em `100%` e estabilidade entre `87,3%` e `93,1%`.

A leitura técnica é que as redes atuais são candidatas promissoras para pesquisa, mas ainda não devem ser promovidas diretamente para operação real. A precisão direcional observada é baixa para uma decisão isolada de compra/venda; portanto, a evolução deve priorizar validação financeira fora da amostra, robustez estatística, controle de vazamento de dados e processo formal de promoção.

## Objetivo do plano

Construir um ciclo profissional de evolução neural para sinais EOD que maximize valor financeiro ajustado ao risco, reduza overfitting e permita promoção controlada de modelos para paper trading e, posteriormente, operação assistida.

## Princípios obrigatórios

1. **Não otimizar apenas acurácia**: priorizar retorno esperado, drawdown, payoff, estabilidade por regime e custo operacional.
2. **Separar treino, validação, teste e paper trading**: nenhuma métrica de treino pode justificar promoção operacional.
3. **Eliminar vazamento temporal**: features, labels e janelas devem respeitar estritamente a disponibilidade no tempo.
4. **Comparar contra baselines simples**: a rede só avança se superar estratégias ingênuas e modelos lineares.
5. **Promover por estágios**: `keep_candidate` -> `backtest_candidate` -> `paper_trade` -> `production_candidate` -> `active`.
6. **Registrar linhagem completa**: dataset, features, arquitetura, pesos, hiperparâmetros, janela temporal, métricas e decisão.

## Fase 0 — Auditoria imediata das candidatas atuais

### Ações

- Congelar os artefatos das melhores variantes atuais para evitar perda de rastreabilidade.
- Validar se a métrica de generalização em `100%` é real ou se há saturação, regra permissiva ou vazamento.
- Conferir se a precisão direcional é calculada apenas sobre sinais emitidos ou sobre todo o universo.
- Verificar duplicidade de modelos no ranking, já que o painel apresenta nomes repetidos com métricas idênticas ou muito próximas.
- Comparar as candidatas atuais por ticker, setor, liquidez, volatilidade e regime de mercado.

### Critério de saída

Apenas modelos com linhagem reprodutível, métricas auditadas e ausência de vazamento seguem para backtest financeiro.

## Fase 1 — Definição de labels e objetivo econômico

### Problema atual

A rede aparentemente está sendo avaliada como classificador direcional, mas o objetivo real é financeiro: gerar sinais que virem trades com expectativa positiva.

### Ações

- Definir labels alinhados ao backtest canônico D->D+1:
  - `trade_triggered`: se o preço tocou entrada no pregão seguinte.
  - `target_before_stop`: se, após entrada, alvo veio antes do stop.
  - `forward_return_net`: retorno líquido esperado após custos.
  - `risk_adjusted_return`: retorno normalizado por volatilidade/ATR.
- Criar labels separados para:
  - probabilidade de entrada;
  - probabilidade de lucro dado que entrou;
  - tamanho esperado do ganho/perda;
  - risco de stop.
- Avaliar abordagem multi-task: uma rede com cabeças diferentes para direção, probabilidade de fill e retorno esperado.

### Critério de saída

Treinar somente modelos cujo label represente diretamente o comportamento financeiro desejado.

## Fase 2 — Engenharia de features com controle temporal

### Features recomendadas

- Retornos defasados: 1, 2, 5, 10, 21 e 63 pregões.
- Volatilidade realizada: 5, 10, 21 e 63 pregões.
- ATR e distância do preço ao range recente.
- Volume relativo contra média de 20 e 60 pregões.
- Gap de abertura, range intradiário e fechamento relativo no candle.
- Tendência por médias móveis e inclinação.
- Reversão à média: z-score contra médias móveis.
- Beta e correlação com IBOV ou índice setorial.
- Regime de mercado: tendência, volatilidade, stress, lateralização.
- Liquidez e filtros de negociabilidade.
- Features cross-sectional: ranking relativo do ativo contra o universo no dia.

### Cuidados

- Toda feature deve usar somente dados disponíveis até o fechamento de D para prever D+1.
- Eventos futuros, máximas/mínimas de D+1 ou dados revisados não podem entrar no dataset de treino.
- Normalização deve ser feita por janela de treino, nunca usando estatísticas globais do período completo.

### Critério de saída

Dataset versionado com testes automáticos de vazamento e features reproduzíveis.

## Fase 3 — Arquiteturas candidatas

### Arquitetura 1 — MLP robusto como baseline neural

- Input tabular normalizado.
- 2 a 4 camadas densas.
- Batch normalization ou layer normalization.
- Dropout moderado.
- Weight decay.
- Early stopping por métrica financeira de validação.

Uso: baseline neural estável e interpretável.

### Arquitetura 2 — Ensemble de MLPs

- Vários MLPs treinados com seeds, janelas e subconjuntos de features diferentes.
- Decisão por média ponderada ou votação calibrada.
- Penalização para modelos altamente correlacionados.

Uso: reduzir variância e instabilidade.

### Arquitetura 3 — Temporal Convolutional Network ou Transformer leve

- Usar sequência de candles/features dos últimos N pregões.
- TCN é preferível como primeiro passo por ser mais simples e menos propenso a overfitting que Transformer em bases pequenas.
- Transformer só deve entrar se houver volume histórico suficiente e validação walk-forward robusta.

Uso: capturar padrões temporais além de features agregadas.

### Arquitetura 4 — Modelo híbrido ranking + classificação

- Primeira etapa ranqueia oportunidades no universo.
- Segunda etapa decide BUY/SELL/NO_TRADE.
- Terceira etapa estima confiança e tamanho de posição.

Uso: reduzir sinais ruins e concentrar capital nos melhores ativos.

## Fase 4 — Treinamento walk-forward

### Protocolo

- Treinar em janela histórica inicial.
- Validar em janela imediatamente posterior.
- Testar em janela realmente fora da amostra.
- Avançar a janela no tempo e repetir.
- Consolidar métricas por fold, não apenas média final.

### Métricas por fold

- Retorno acumulado.
- Sharpe, Sortino e Calmar.
- Drawdown máximo.
- Hit rate.
- Profit factor.
- Payoff médio.
- Número de trades.
- Exposição média.
- Turnover.
- Pior mês e pior sequência de perdas.

### Critério de saída

Modelo só avança se apresentar resultado positivo e estável em múltiplos folds, sem depender de um único período excepcional.

## Fase 5 — Função de score para seleção

Substituir ou complementar o score atual por um score financeiro composto:

```text
score_final =
  0.30 * retorno_ajustado_ao_risco
+ 0.20 * estabilidade_walk_forward
+ 0.15 * profit_factor
+ 0.15 * controle_drawdown
+ 0.10 * cobertura_util
+ 0.10 * robustez_por_regime
- penalidades
```

### Penalidades

- Baixo número de trades.
- Alta concentração em poucos tickers.
- Drawdown excessivo.
- Degradação forte fora da amostra.
- Alta correlação com modelo já aprovado.
- Dependência de custos irrealistas.

## Fase 6 — Calibração de decisão e sizing

### Ações

- Calibrar probabilidades com Platt scaling ou isotonic regression.
- Definir thresholds diferentes para BUY, SELL e NO_TRADE.
- Usar zona morta: se confiança for insuficiente, não operar.
- Converter confiança em tamanho de posição limitado.
- Aplicar filtros de liquidez, volatilidade e exposição setorial.

### Regras iniciais sugeridas

- Máximo de 5 sinais por dia, mantendo compatibilidade operacional atual.
- Máximo de exposição por ativo.
- Máximo de exposição por setor.
- Não operar tickers com baixa liquidez ou dados incompletos.
- Bloquear operação em regime de stress se o modelo não performa bem nesse regime.

## Fase 7 — Backtest com custos realistas

### Custos e fricções obrigatórios

- Corretagem, emolumentos e taxas.
- Slippage por liquidez.
- Diferença entre preço teórico e preço executável.
- Limite de volume negociável por ativo.
- Regras distintas para abertura, mínima/máxima e fechamento.

### Critério de saída

A rede só pode ir para paper trading se superar baselines após custos e com drawdown aceitável.

## Fase 8 — Paper trading e monitoramento

### Métricas de acompanhamento diário

- Sinais emitidos.
- Sinais filtrados.
- Sinais que geraram trade.
- Retorno diário e acumulado.
- Drawdown em paper.
- Desvio entre backtest esperado e paper realizado.
- Distribuição por ticker/setor/regime.
- Drift de features.
- Queda de calibração da probabilidade.

### Regras de parada

- Drawdown acima do limite.
- Queda forte de hit rate ou profit factor.
- Drift estatístico relevante nas features.
- Divergência persistente entre paper e backtest.
- Erros de dados ou buracos de cotação.

## Fase 9 — Evolução genética/neural controlada

### Mutação permitida

- Hiperparâmetros: learning rate, dropout, weight decay, batch size.
- Arquitetura: número de camadas, largura, ativação.
- Features: subconjuntos e transformações.
- Thresholds: corte de confiança e filtros de risco.

### Mutação proibida sem validação especial

- Alterar label sem versionamento.
- Usar features não auditadas.
- Otimizar diretamente no período de teste.
- Selecionar modelo por métrica única.

### Seleção

- Manter diversidade entre modelos.
- Penalizar modelos muito parecidos.
- Requerer melhoria estatisticamente relevante contra campeão atual.
- Promover challenger apenas após paper trading comparativo.

## Roadmap recomendado

### Semana 1

- Auditar métricas atuais.
- Congelar top candidatas.
- Validar vazamento temporal.
- Criar relatório de performance por ticker/regime.

### Semana 2

- Implementar score financeiro composto.
- Rodar backtest fora da amostra para top modelos.
- Comparar contra baselines simples.

### Semana 3

- Melhorar labels e features.
- Treinar MLP baseline robusto e ensemble.
- Rodar walk-forward.

### Semana 4

- Calibrar thresholds.
- Implantar paper trading com painel de monitoramento.
- Definir campeão e challengers.

### Semanas 5 a 8

- Testar TCN/modelo sequencial.
- Evoluir ensemble.
- Implantar detecção de drift.
- Formalizar promoção controlada.

## Decisão recomendada para as redes atuais

As redes atuais devem permanecer em `keep_candidate` até auditoria. As melhores variantes por score/cobertura/estabilidade podem ser promovidas somente para `backtest_candidate`, não para produção. O próximo passo concreto é auditar métricas e rodar backtest financeiro fora da amostra com custos realistas.
