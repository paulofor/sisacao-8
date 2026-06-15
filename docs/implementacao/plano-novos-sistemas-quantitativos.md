# Plano de implementação — novos sistemas quantitativos com telas de acompanhamento

## 1. Objetivo

Criar uma esteira de pesquisa, backtest, validação e monitoramento para novos sistemas quantitativos de ações, usando os dados já disponíveis no projeto Sisacao-8. O foco é deixar de depender de um único sinal inicial e passar a operar como um laboratório de estratégias com comparação objetiva entre hipóteses.

O plano prioriza sistemas simples, auditáveis e estatisticamente testáveis antes de qualquer aumento de complexidade com machine learning. Cada fase inclui telas específicas para que o usuário acompanhe resultados, qualidade estatística e evolução das estratégias.

## 2. Princípios de decisão

- Nenhum sistema deve ser considerado promissor apenas por uma sequência curta de trades.
- Toda estratégia deve ser avaliada líquida de custos, slippage e regras realistas de execução.
- O primeiro objetivo não é maximizar retorno, mas descobrir se existe expectativa matemática positiva e estável.
- O dashboard deve mostrar também evidências negativas: drawdown, deterioração recente, baixa amostra, concentração por ativo e sensibilidade a parâmetros.
- Estratégias simples e interpretáveis devem ser usadas como baseline antes de modelos complexos.
- Toda comparação entre sistemas deve usar o mesmo motor de backtest e o mesmo conjunto de métricas.

## 3. Famílias de sistemas a pesquisar

| Família | Hipótese de mercado | Exemplo de uso |
|---|---|---|
| Ranking de ações | Escolher os ativos relativamente mais fortes ou mais assimétricos do universo disponível | Comprar os 3 a 5 melhores ativos do dia |
| Momentum com volume | Movimento forte com volume tende a continuar por curto período | Compra após força relativa e volume acima da média |
| Reversão à média | Exageros de curto prazo tendem a corrigir parcialmente | Compra após queda forte em ativo ainda saudável |
| Rompimento | Quebra de máxima/mínima com volume indica entrada de fluxo | Compra no rompimento confirmado |
| Gap | Gaps podem continuar ou fechar conforme contexto | Gap continuation ou gap fade |
| Regime de mercado | O ambiente do índice determina quando operar ou ficar fora | Ativar compras apenas em regime favorável |
| Intraday por horário | Certas janelas do pregão têm comportamento diferente | Evitar almoço, estudar abertura e fechamento |

## 4. Fase 0 — Preparação e inventário dos dados

**Status:** executada em 2026-06-14. Relatório técnico: [`docs/implementacao/fase0-inventario-dados-quantitativos.md`](fase0-inventario-dados-quantitativos.md). Script BigQuery: [`infra/bq/07_quant_phase0_inventory.sql`](../../infra/bq/07_quant_phase0_inventory.sql).

### Objetivo

Mapear exatamente quais dados existem, qual a granularidade, quais ativos estão disponíveis, qual período histórico é confiável e quais lacunas precisam ser tratadas antes de gerar novos sistemas.

### Entregáveis técnicos

- Inventário das tabelas BigQuery usadas por cotação, sinais, backtests, métricas, qualidade e configuração.
- Relatório de cobertura por ticker, data, volume e periodicidade.
- Identificação de lacunas, duplicidades, candles inválidos, preços zerados e inconsistências de calendário.
- Definição do universo inicial de ativos elegíveis por liquidez e qualidade de dados.

### Telas de acompanhamento

#### Tela: Inventário de Dados

Componentes sugeridos:

- Cards de resumo:
  - quantidade de tickers ativos;
  - período histórico disponível;
  - total de candles diários;
  - total de candles intraday;
  - percentual de dados válidos;
  - última atualização.
- Tabela de cobertura por ticker:
  - ticker;
  - primeira data;
  - última data;
  - dias com dados;
  - dias esperados;
  - percentual de cobertura;
  - volume médio;
  - status de elegibilidade.
- Gráfico de calor de ausência de dados por ticker e data.
- Filtros por ticker, setor, liquidez e período.

#### Tela: Qualidade dos Dados

Componentes sugeridos:

- Cards de incidentes:
  - candles faltantes;
  - preços zerados;
  - volumes zerados;
  - duplicidades;
  - outliers extremos;
  - divergências de calendário.
- Gráfico temporal de incidentes por dia.
- Tabela de incidentes com severidade, ticker, data, tipo e recomendação.
- Indicador visual de `apto para backtest` por ticker.

### Critérios de saída

- Pelo menos um universo inicial de ativos elegíveis definido.
- Regras de exclusão documentadas.
- Dados mínimos suficientes para rodar backtests comparáveis.

## 5. Fase 1 — Motor comum de backtest e métricas

**Status:** preparada em 2026-06-14. Relatório técnico: [`docs/implementacao/fase1-motor-backtest-metricas.md`](fase1-motor-backtest-metricas.md). Script BigQuery: [`infra/bq/08_quant_phase1_backtest_engine.sql`](../../infra/bq/08_quant_phase1_backtest_engine.sql).

### Objetivo

Criar um motor único de backtest para evitar que cada estratégia tenha regras próprias de execução, custos e métricas. Isso reduz viés e permite comparação justa.

### Entregáveis técnicos

- Modelo padronizado de entrada de estratégia:
  - ticker;
  - data/hora do sinal;
  - lado da operação;
  - preço de entrada esperado;
  - regra de saída;
  - horizonte máximo;
  - metadados da versão.
- Modelo padronizado de trade:
  - entrada;
  - saída;
  - PnL bruto;
  - PnL líquido;
  - custo estimado;
  - slippage;
  - outcome;
  - motivo de saída.
- Métricas consolidadas por estratégia, versão, período, ticker e regime.

### Telas de acompanhamento

#### Tela: Laboratório de Backtests

Componentes sugeridos:

- Seletor de estratégia e versão.
- Seletor de período e universo de ativos.
- Cards principais:
  - número de sinais;
  - número de trades;
  - win rate;
  - payoff médio;
  - expectancy líquida;
  - profit factor;
  - max drawdown;
  - Sharpe/Sortino, quando aplicável.
- Curva de capital.
- Gráfico de drawdown.
- Histograma de PnL por trade.
- Distribuição de outcomes: target, stop, expire, manual, time stop.
- Tabela paginada de trades.

#### Tela: Comparador de Estratégias

Componentes sugeridos:

- Tabela comparativa por estratégia e versão:
  - retorno líquido;
  - profit factor;
  - drawdown;
  - trades;
  - win rate;
  - expectancy;
  - estabilidade mensal;
  - score de robustez.
- Gráfico de dispersão:
  - eixo X: drawdown;
  - eixo Y: retorno ou expectancy;
  - tamanho do ponto: número de trades;
  - cor: família da estratégia.
- Ranking automático das estratégias por critérios configuráveis.

### Critérios de saída

- Qualquer nova estratégia deve conseguir rodar no mesmo motor.
- Métricas precisam ser comparáveis entre estratégias.
- Custos e slippage devem aparecer explicitamente.

## 6. Fase 2 — Sistemas baseline simples

**Status:** preparada em 2026-06-14. Relatório técnico: [`docs/implementacao/fase2-sistemas-baseline-simples.md`](fase2-sistemas-baseline-simples.md). Script BigQuery: [`infra/bq/09_quant_phase2_baseline_systems.sql`](../../infra/bq/09_quant_phase2_baseline_systems.sql).

### Objetivo

Criar estratégias simples para medir se há estrutura explorável nos dados. Elas servem como referência para qualquer abordagem mais avançada.

### Estratégias iniciais

1. Momentum diário simples.
2. Reversão à média diária.
3. Rompimento de máxima/mínima.
4. Gap continuation e gap fade.
5. Ranking diário por força relativa.
6. Filtro de regime do Ibovespa.

### Telas de acompanhamento

#### Tela: Estratégias Baseline

Componentes sugeridos:

- Cards por família de estratégia com status:
  - não iniciada;
  - em teste;
  - reprovada;
  - promissora;
  - candidata a validação.
- Mini curva de capital por baseline.
- Indicadores mínimos:
  - trades;
  - expectancy líquida;
  - profit factor;
  - drawdown;
  - estabilidade mensal.
- Botão de navegação para detalhes da estratégia.

#### Tela: Detalhe da Estratégia

Componentes sugeridos:

- Descrição da hipótese de mercado.
- Regras de entrada e saída.
- Parâmetros usados.
- Métricas gerais.
- Métricas por ticker.
- Métricas por mês.
- Métricas por regime de mercado.
- Lista de piores trades e melhores trades.
- Alertas automáticos:
  - amostra insuficiente;
  - lucro concentrado em poucos trades;
  - drawdown elevado;
  - resultado sensível a um único ativo.

### Critérios de saída

- Pelo menos uma baseline deve mostrar expectativa líquida positiva antes de evoluir para modelos mais sofisticados.
- Estratégias sem vantagem devem ser mantidas como referência, mas marcadas como reprovadas.

## 7. Fase 3 — Ranking e seleção de ativos

**Status:** preparada em 2026-06-15. Relatório técnico: [`docs/implementacao/fase3-ranking-selecao-ativos.md`](fase3-ranking-selecao-ativos.md). Script BigQuery: [`infra/bq/10_quant_phase3_asset_ranking.sql`](../../infra/bq/10_quant_phase3_asset_ranking.sql).

### Objetivo

Evoluir de sinais isolados para um modelo de ranking, escolhendo os melhores ativos relativos do universo disponível.

### Entregáveis técnicos

- Score composto por fatores como:
  - força relativa;
  - momentum curto;
  - volume relativo;
  - volatilidade;
  - distância da média;
  - qualidade do candle;
  - regime do índice.
- Backtest de carteiras top N:
  - top 3;
  - top 5;
  - top 10.
- Comparação entre ranking simples e ranking ponderado.

### Telas de acompanhamento

#### Tela: Ranking Diário de Oportunidades

Componentes sugeridos:

- Tabela dos ativos ranqueados:
  - posição;
  - ticker;
  - score final;
  - fatores que contribuíram;
  - preço atual;
  - liquidez;
  - risco estimado;
  - sugestão: operar, observar ou evitar.
- Cards de mercado:
  - regime atual;
  - volatilidade do índice;
  - número de ativos em tendência;
  - amplitude do mercado.
- Gráfico de decomposição do score por ticker.
- Selo de confiança do sinal com base em histórico semelhante.

#### Tela: Performance do Ranking

Componentes sugeridos:

- Retorno histórico de top 3, top 5 e top 10.
- Comparação contra seleção aleatória.
- Comparação contra Ibovespa.
- Matriz de acerto por decil do ranking.
- Gráfico mostrando se os ativos com score maior realmente performaram melhor.

### Critérios de saída

- O ranking precisa mostrar monotonicidade: grupos com score maior devem ter retorno médio melhor que grupos com score menor.
- O top N deve superar seleção aleatória após custos.

## 8. Fase 4 — Filtros de regime e controle de exposição

### Objetivo

Evitar operar em ambientes ruins. Esta fase decide quando o sistema deve operar, reduzir mão, operar vendido ou ficar fora.

### Entregáveis técnicos

- Classificação de regime:
  - alta tendência;
  - baixa tendência;
  - lateral;
  - alta volatilidade;
  - baixa volatilidade;
  - stress.
- Regras de exposição:
  - operar normal;
  - reduzir posição;
  - bloquear compras;
  - bloquear vendas;
  - ficar em caixa.

### Telas de acompanhamento

#### Tela: Regime de Mercado

Componentes sugeridos:

- Card com regime atual.
- Histórico de regimes por data.
- Indicadores do regime:
  - tendência do Ibovespa;
  - volatilidade realizada;
  - amplitude do mercado;
  - percentual de ativos acima da média;
  - volume agregado.
- Gráfico de performance das estratégias por regime.
- Alerta operacional quando o regime atual for historicamente desfavorável.

#### Tela: Exposição Recomendada

Componentes sugeridos:

- Exposição máxima sugerida para o dia.
- Quantidade máxima de operações.
- Limite de risco por trade.
- Limite de perda diária.
- Justificativa da recomendação com base no regime.

### Critérios de saída

- Estratégias devem apresentar melhora de drawdown ou expectancy quando filtradas por regime.
- Regras de bloqueio devem reduzir operações ruins sem eliminar excessivamente os bons trades.

## 9. Fase 5 — Validação estatística e robustez

### Objetivo

Separar estratégias que apenas encaixaram no passado daquelas que têm alguma estabilidade estatística.

### Entregáveis técnicos

- Validação out-of-sample.
- Walk-forward analysis.
- Teste por subperíodos.
- Teste por grupos de ativos.
- Teste de sensibilidade a parâmetros.
- Teste com custos ampliados.
- Comparação contra aleatorização.

### Telas de acompanhamento

#### Tela: Validação e Robustez

Componentes sugeridos:

- Cards:
  - resultado em treino;
  - resultado em validação;
  - resultado em teste;
  - degradação fora da amostra;
  - score de robustez.
- Gráfico de walk-forward.
- Heatmap de parâmetros:
  - eixo X: parâmetro 1;
  - eixo Y: parâmetro 2;
  - cor: expectancy ou profit factor.
- Painel de custos:
  - resultado sem custo;
  - custo normal;
  - custo estressado;
  - slippage estressado.
- Alertas de overfitting.

### Critérios de saída

- Estratégia candidata deve manter expectativa positiva fora da amostra.
- Resultado não pode depender de um único parâmetro exato.
- Resultado não pode desaparecer com custos realistas.

## 10. Fase 6 — Simulação operacional em paper trading

### Objetivo

Acompanhar os sinais em tempo quase real sem colocar capital real, medindo se a operação simulada se comporta como o backtest.

### Entregáveis técnicos

- Geração diária/intraday de sinais candidatos.
- Registro de decisões do sistema.
- Simulação de entrada, saída, custos e slippage.
- Comparação entre resultado esperado e realizado.

### Telas de acompanhamento

#### Tela: Paper Trading

Componentes sugeridos:

- Operações abertas simuladas.
- Operações encerradas do dia.
- PnL diário simulado.
- PnL acumulado simulado.
- Aderência ao backtest:
  - preço esperado vs preço simulado;
  - slippage médio;
  - taxa de execução;
  - divergência de resultado.
- Botão para marcar observações manuais.

#### Tela: Diário Operacional

Componentes sugeridos:

- Lista de eventos do dia:
  - sinal gerado;
  - sinal filtrado;
  - entrada simulada;
  - stop;
  - target;
  - expire;
  - alerta de risco.
- Comentários do usuário por operação.
- Exportação para análise posterior.

### Critérios de saída

- Paper trading deve rodar por período mínimo definido antes de capital real.
- Divergência entre backtest e simulação precisa ser explicada.
- Estratégia deve manter expectativa compatível com o histórico.

## 11. Fase 7 — Preparação para operação controlada

### Objetivo

Caso uma ou mais estratégias sobrevivam às fases anteriores, preparar operação real em escala reduzida e com controles rígidos de risco.

### Entregáveis técnicos

- Checklist de liberação por estratégia.
- Configuração de risco:
  - capital máximo;
  - risco por trade;
  - limite diário;
  - limite semanal;
  - limite por ativo;
  - limite por setor.
- Monitoramento de execução e alertas.

### Telas de acompanhamento

#### Tela: Comitê de Estratégias

Componentes sugeridos:

- Lista de estratégias candidatas.
- Status de aprovação:
  - pesquisa;
  - validação;
  - paper trading;
  - piloto;
  - reprovada;
  - pausada.
- Checklist de critérios:
  - amostra mínima;
  - expectativa positiva;
  - drawdown aceitável;
  - validação fora da amostra;
  - paper trading consistente;
  - risco aprovado.
- Campo de decisão manual: aprovar, pausar ou reprovar.

#### Tela: Risco e Limites

Componentes sugeridos:

- Exposição atual por estratégia.
- Exposição por ticker.
- Risco máximo do dia.
- Perda acumulada do dia.
- Limites violados.
- Alertas de desligamento automático.

### Critérios de saída

- Nenhuma estratégia deve ir para operação sem checklist completo.
- O sistema deve permitir pausar estratégia imediatamente.
- Limites de risco devem ser visíveis e auditáveis.

## 12. Modelo de dados sugerido

Novas tabelas ou entidades podem ser criadas gradualmente, conforme a implementação evoluir.

| Entidade | Objetivo |
|---|---|
| `strategy_registry` | Cadastro de estratégias, famílias, versões e status |
| `strategy_parameters` | Parâmetros versionados por estratégia |
| `strategy_signals` | Sinais gerados por cada estratégia |
| `strategy_backtest_runs` | Execuções de backtest com metadados |
| `strategy_backtest_trades` | Trades simulados por execução |
| `strategy_backtest_metrics` | Métricas agregadas por execução |
| `strategy_rankings` | Rankings diários/intraday de ativos |
| `market_regimes` | Classificação histórica e atual de regimes |
| `paper_trading_orders` | Ordens simuladas e estado operacional |
| `strategy_decisions_log` | Log auditável de decisões automáticas e manuais |

## 13. Priorização recomendada

### Sprint A — Fundação

- Inventário de dados.
- Tela de Inventário de Dados.
- Tela de Qualidade dos Dados.
- Definição do universo elegível.

### Sprint B — Backtest comum

- Motor de backtest padronizado.
- Tela Laboratório de Backtests.
- Tela Comparador de Estratégias.

### Sprint C — Baselines

- Momentum simples.
- Reversão simples.
- Rompimento simples.
- Ranking simples.
- Tela Estratégias Baseline.
- Tela Detalhe da Estratégia.

### Sprint D — Ranking e regime

- Ranking diário de oportunidades.
- Classificação de regime de mercado.
- Tela Ranking Diário.
- Tela Regime de Mercado.

### Sprint E — Robustez

- Walk-forward.
- Out-of-sample.
- Sensibilidade a parâmetros.
- Tela Validação e Robustez.

### Sprint F — Paper trading

- Simulação operacional.
- Tela Paper Trading.
- Tela Diário Operacional.

### Sprint G — Piloto controlado

- Comitê de estratégias.
- Tela Risco e Limites.
- Checklist de aprovação.

## 14. Métricas mínimas para qualquer tela de estratégia

Toda tela de estratégia deve exibir, no mínimo:

- número de trades;
- período testado;
- win rate;
- payoff médio;
- expectancy bruta;
- expectancy líquida;
- profit factor;
- retorno acumulado;
- max drawdown;
- exposição média;
- pior sequência de perdas;
- resultado por ticker;
- resultado por mês;
- resultado por regime;
- custo total estimado;
- slippage estimado;
- alerta de amostra insuficiente.

## 15. Regras de aprovação de estratégia

Uma estratégia só deve avançar de fase quando atender aos critérios mínimos:

1. Amostra suficiente para a frequência proposta.
2. Expectancy líquida positiva.
3. Profit factor acima de 1,2 como corte inicial exploratório.
4. Drawdown compatível com o capital e o risco permitido.
5. Resultado não concentrado em um único ticker ou em poucos trades.
6. Robustez em múltiplos períodos.
7. Sobrevivência a custos e slippage estressados.
8. Validação fora da amostra sem degradação excessiva.
9. Paper trading coerente com backtest.
10. Checklist de risco aprovado.

## 16. Próximo passo recomendado

O próximo passo prático é implementar a Fase 0 e a Fase 1. Sem inventário confiável e sem motor comum de backtest, qualquer nova estratégia corre o risco de ser comparada de forma injusta ou gerar conclusões frágeis.

A primeira entrega visual deve ser o conjunto:

1. Tela de Inventário de Dados.
2. Tela de Qualidade dos Dados.
3. Tela Laboratório de Backtests.
4. Tela Comparador de Estratégias.

Com essas telas, o projeto passa a ter uma base objetiva para decidir quais sistemas merecem evolução e quais devem ser descartados rapidamente.
