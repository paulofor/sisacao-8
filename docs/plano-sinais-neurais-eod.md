# Plano — Sistema de sinais EOD com redes neurais

## 1. Objetivo

Criar um novo sistema de sinais de fim de dia (EOD) baseado em redes neurais, mantendo a mesma lógica operacional já usada pelo pipeline atual:

1. fechar o pregão;
2. gerar um sinal válido para o próximo pregão;
3. definir preço de entrada com percentual de diferença em relação ao fechamento;
4. definir `target`, `stop` e horizonte;
5. gravar o sinal em tabela auditável;
6. deixar o `backtest_daily` validar o resultado nos dias seguintes.

A mudança principal é substituir o ranking heurístico atual por uma camada neural de predição, sem remover as regras de risco, liquidez, auditoria e governança.

## 2. Princípio de arquitetura

A rede neural não deve gravar diretamente em `sinais_eod`.

O desenho recomendado é:

```text
candles/features EOD
    ↓
modelo neural versionado
    ↓
tabela de predições neurais
    ↓
camada de decisão EOD
    ↓
sinais com entrada/target/stop
    ↓
backtest diário
```

Essa separação permite auditar a diferença entre:

- predição bruta do modelo;
- decisão operacional;
- filtros de risco;
- sinais efetivamente liberados;
- resultado posterior no backtest.

## 3. Regra operacional desejada

Para cada ativo elegível no fechamento do pregão `D`, o modelo neural deve estimar probabilidades para o movimento futuro:

- `prob_up`: probabilidade de alta;
- `prob_down`: probabilidade de queda;
- `prob_neutral`: probabilidade de movimento neutro.

A camada de decisão transforma essas probabilidades em intenção operacional:

- `BUY` quando `prob_up` superar um limiar mínimo de confiança;
- `SELL` quando `prob_down` superar um limiar mínimo de confiança;
- `HOLD` quando nenhuma probabilidade direcional superar o limiar.

Somente intenções `BUY` e `SELL` podem virar sinais.

## 4. Lógica de entrada com percentual de diferença

A lógica de entrada deve continuar parecida com a atual, sempre calculada a partir do fechamento do pregão `D`.

### 4.1 Sinal de compra

Para `BUY`, a entrada fica abaixo do fechamento:

```text
entry = close(D) * (1 - x_pct)
target = entry * (1 + target_pct)
stop = entry * (1 - stop_pct)
```

Exemplo:

```text
close(D) = 100,00
x_pct = 0,02
entry = 98,00
target_pct = 0,07 → target = 104,86
stop_pct = 0,07 → stop = 91,14
```

### 4.2 Sinal de venda

Para `SELL`, a entrada fica acima do fechamento:

```text
entry = close(D) * (1 + x_pct)
target = entry * (1 - target_pct)
stop = entry * (1 + stop_pct)
```

Exemplo:

```text
close(D) = 100,00
x_pct = 0,02
entry = 102,00
target_pct = 0,07 → target = 94,86
stop_pct = 0,07 → stop = 109,14
```

## 5. Componentes a criar

### 5.1 Tabela de predições neurais

Criar uma tabela BigQuery para armazenar as saídas brutas do modelo antes da decisão operacional.

Nome sugerido:

```text
cotacao_intraday.neural_eod_predictions
```

Campos sugeridos:

| Campo | Tipo | Descrição |
|---|---|---|
| `reference_date` | DATE | Pregão usado como base da predição. |
| `valid_for` | DATE | Próximo pregão em que a predição pode virar sinal. |
| `ticker` | STRING | Ativo. |
| `model_id` | STRING | Identificador do modelo neural. |
| `model_version` | STRING | Versão treinada/promovida. |
| `feature_version` | STRING | Versão do conjunto de features. |
| `prob_up` | FLOAT64 | Probabilidade de alta. |
| `prob_down` | FLOAT64 | Probabilidade de queda. |
| `prob_neutral` | FLOAT64 | Probabilidade neutra. |
| `suggested_action` | STRING | `BUY`, `SELL` ou `HOLD`. |
| `confidence` | FLOAT64 | Maior probabilidade direcional usada na decisão. |
| `created_at` | TIMESTAMP | Data/hora de geração. |
| `source_snapshot` | STRING | Hash dos dados usados na inferência. |
| `job_run_id` | STRING | ID da execução. |

### 5.2 Job de inferência neural EOD

Criar uma nova função/job, sugerido:

```text
functions/neural_eod_predictions/
```

Responsabilidades:

1. receber `date_ref` opcional;
2. validar cutoff e dia útil;
3. carregar candles/features até o fechamento de `date_ref`;
4. carregar o modelo neural aprovado;
5. gerar probabilidades por ticker;
6. converter probabilidades em `BUY`, `SELL` ou `HOLD`;
7. gravar as predições em `neural_eod_predictions`;
8. não gravar diretamente em `sinais_eod`.

### 5.3 Adaptação do `eod_signals`

Depois que as predições estiverem disponíveis, criar um modo neural no `eod_signals`.

Nome sugerido de parâmetro:

```text
SIGNAL_SOURCE=heuristic|neural|hybrid
```

Modos:

- `heuristic`: comportamento atual;
- `neural`: usa apenas predições neurais aprovadas;
- `hybrid`: combina score neural com score heurístico/backtest/liquidez.

No modo neural, o `eod_signals` deve:

1. ler `neural_eod_predictions` para `date_ref`;
2. descartar ações `HOLD`;
3. aplicar confiança mínima;
4. aplicar liquidez mínima;
5. aplicar limite máximo de sinais;
6. calcular `entry`, `target`, `stop` e `horizon_days`;
7. gravar em `sinais_eod` com `model_version` neural.

### 5.4 Backtest diário

O `backtest_daily` deve continuar sendo o validador.

A princípio, ele não precisa mudar, porque já consome os campos operacionais do sinal:

- `date_ref`;
- `valid_for`;
- `ticker`;
- `side`;
- `entry`;
- `target`;
- `stop`;
- `horizon_days`;
- `model_version`.

O ponto essencial é garantir que sinais neurais sejam gravados em `sinais_eod` com versão/modelo rastreável, por exemplo:

```text
model_version = neural_eod_mlp_v1
ranking_key = neural_confidence_v1
```

## 6. Features iniciais recomendadas

Para a primeira versão, evitar complexidade excessiva. Usar features simples e auditáveis:

- retornos dos últimos 5, 10 e 20 pregões;
- volatilidade dos últimos 10 e 20 pregões;
- range diário: `(high - low) / close`;
- variação intradiária: `(close - open) / open`;
- volume financeiro normalizado;
- média móvel de volume;
- distância do fechamento para máximas/mínimas recentes;
- flags de qualidade de dados.

O objetivo inicial não é maximizar sofisticação, mas criar um baseline neural comparável com as estratégias existentes.

## 7. Critérios mínimos para virar sinal

Uma predição neural só deve virar sinal se passar por critérios mínimos:

| Critério | Sugestão inicial |
|---|---|
| Confiança mínima BUY | `prob_up >= 0.60` |
| Confiança mínima SELL | `prob_down >= 0.60` |
| Liquidez mínima | reutilizar `MIN_SIGNAL_VOLUME` |
| Máximo de sinais por dia | 5 |
| Horizonte | 15 pregões ou parâmetro versionado |
| Entrada | percentual `x_pct` contra o fechamento |
| Target/stop | percentuais versionados |
| Modelo | somente versão aprovada para inferência |

Esses valores devem ser tratados como parâmetros versionados e não como constantes fixas definitivas.

## 8. Fases de implementação

### Fase 1 — Especificação e schema

**Status:** executada em 2026-06-18. Detalhes em `docs/implementacao/fase1-sinais-neurais-eod-schema.md`; DDL em `infra/bq/16_neural_eod_predictions.sql`.

- [x] Criar DDL da tabela `neural_eod_predictions`.
- [x] Definir schema mínimo de features.
- [x] Definir convenção de `model_id`, `model_version` e `feature_version`.
- [x] Documentar contratos de entrada/saída.

### Fase 2 — Dataset de treino

**Status:** executada em 2026-06-18. Detalhes em `docs/implementacao/fase2-sinais-neurais-eod-dataset.md`; código em `sisacao8/neural_dataset.py`; DDL em `infra/bq/17_neural_eod_training_dataset.sql`.

- [x] Montar dataset histórico por ticker/data.
- [x] Criar labels `up`, `down`, `neutral` usando horizonte e threshold versionados.
- [x] Separar treino/validação/teste em ordem cronológica.
- [x] Evitar vazamento temporal.

### Fase 3 — Treino neural baseline

**Status:** executada em 2026-06-18. Detalhes em `docs/implementacao/fase3-sinais-neurais-eod-treino-baseline.md`; código em `sisacao8/neural_training.py`; registro BigQuery em `infra/bq/18_neural_model_registry.sql`.

- [x] Começar com MLP simples.
- [x] Registrar métricas por classe.
- [x] Avaliar matriz de confusão, precisão direcional e cobertura.
- [x] Salvar artefato do modelo com versão.

### Fase 4 — Inferência EOD sem produção

**Status:** executada em 2026-06-19. Detalhes em `docs/implementacao/fase4-sinais-neurais-eod-inferencia.md`; código em `sisacao8/neural_inference.py` e `functions/neural_eod_predictions/`.

- [x] Criar job `neural_eod_predictions`.
- [x] Rodar diariamente após o fechamento.
- [x] Gravar apenas predições, sem gerar sinais operacionais.
- [x] Validar estabilidade dos outputs por alguns pregões.

### Fase 5 — Sinais neurais em paralelo

- Ativar modo `neural` ou `hybrid` em ambiente controlado.
- Gravar sinais neurais com `model_version` própria.
- Não substituir imediatamente os sinais heurísticos.
- Comparar resultados via `backtest_daily`.

### Fase 6 — Paper trading

- Liberar somente se o backtest neural superar critérios mínimos.
- Monitorar fill rate, win rate, retorno médio, profit factor, drawdown e sensibilidade a custos.
- Manter limites baixos e logs completos.

### Fase 7 — Promoção controlada

- Promover apenas modelos com robustez fora da amostra.
- Exigir aprovação explícita antes de qualquer uso com capital real.
- Manter fallback para `heuristic`.

## 9. Métricas de avaliação

Avaliar o sistema neural em três níveis.

### 9.1 Métricas do modelo

- accuracy;
- precision por classe;
- recall por classe;
- matriz de confusão;
- calibração das probabilidades;
- taxa de `HOLD`.

### 9.2 Métricas dos sinais

- sinais por dia;
- distribuição BUY/SELL;
- confiança média;
- fill rate;
- taxa de stop/target;
- retorno médio por trade;
- profit factor;
- win rate;
- tempo médio em trade.

### 9.3 Métricas operacionais

- latência do job;
- quantidade de ativos processados;
- falhas por dados ausentes;
- divergência entre universo esperado e universo processado;
- rastreabilidade por `job_run_id` e `source_snapshot`.

## 10. Riscos e controles

| Risco | Controle recomendado |
|---|---|
| Overfitting | split temporal, walk-forward e teste fora da amostra. |
| Vazamento temporal | features somente até `date_ref`; labels somente para treino histórico. |
| Baixa calibração de probabilidades | calibração e thresholds conservadores. |
| Ativos sem liquidez | filtro mínimo de volume financeiro. |
| Mudança de regime | monitoramento por regime e revalidação periódica. |
| Substituição prematura do sistema atual | rodar em paralelo antes de promover. |
| Falta de auditoria | tabela de predições + `source_snapshot` + versão do modelo. |

## 11. Critério de pronto para primeira versão

A primeira versão será considerada pronta quando:

1. a tabela `neural_eod_predictions` estiver criada;
2. o job de inferência gravar predições diariamente;
3. o modelo tiver versão rastreável;
4. o `eod_signals` conseguir consumir predições neurais em modo controlado;
5. os sinais neurais forem gravados em `sinais_eod` sem quebrar o `backtest_daily`;
6. houver comparação diária entre heurístico, neural e híbrido;
7. o diário do projeto registrar execuções, falhas e decisões de promoção/bloqueio.

## 12. Decisão inicial recomendada

Começar pelo modo `neural` em paralelo, sem substituir o fluxo atual.

A sequência recomendada é:

```text
1. criar tabela neural_eod_predictions
2. criar job neural_eod_predictions
3. gerar predições diárias sem sinais
4. adaptar eod_signals com SIGNAL_SOURCE=neural
5. gerar sinais neurais em paralelo
6. validar via backtest_daily
7. decidir se evolui para hybrid ou promoção controlada
```

## 13. Plano completo de treino e seleção de redes neurais

Esta seção detalha o processo recomendado para construir, treinar, comparar e promover redes neurais para sinais EOD. O foco é evitar vazamento temporal, reduzir overfitting e selecionar modelos que gerem valor operacional depois de custos, não apenas boa métrica estatística.

### 13.1 Premissas financeiras e escopo do primeiro ciclo

- **Mercado-alvo:** ações B3 com histórico diário confiável, liquidez mínima e cadastro ativo em `cotacao_intraday.acao_bovespa`.
- **Frequência de decisão:** uma inferência por ativo no fechamento do pregão `D`, válida para tentativa de entrada em `D+1`.
- **Regra de execução:** manter a regra canônica do projeto: BUY tenta entrada em `close(D) * (1 - x_pct)` e SELL tenta entrada em `close(D) * (1 + x_pct)`.
- **Objetivo do modelo:** estimar probabilidades calibradas de movimento favorável, adverso ou neutro no horizonte operacional, para alimentar a camada de decisão; o modelo não deve decidir sozinho tamanho de posição nem gravar diretamente sinais finais.
- **Restrições:** nenhum dado posterior ao fechamento de `D` pode entrar nas features do exemplo `(ticker, D)`.

### 13.2 Separação de dados: treino, validação, teste e paper trading

A separação deve ser temporal, nunca aleatória por linha, porque séries financeiras têm autocorrelação, mudança de regime e dependência entre ativos no mesmo pregão.

| Partição | Uso | Sugestão inicial | Pode ajustar hiperparâmetro? |
|---|---|---:|---|
| Treino | Ajustar pesos da rede | 60% a 70% mais antigo do histórico | Sim |
| Validação | Escolher arquitetura, thresholds e early stopping | 15% a 20% intermediário | Sim, com parcimônia |
| Teste fora da amostra | Medir desempenho final antes de paper trading | 15% a 20% mais recente antes do paper | Não |
| Paper trading | Validação prospectiva diária, sem capital real | mínimo 60 pregões, ideal 120+ | Não para o mesmo ciclo |

Regras obrigatórias:

1. **Split por data:** todos os tickers de uma mesma data devem ficar na mesma partição.
2. **Embargo temporal:** deixar uma folga entre treino e validação/teste maior ou igual ao `horizon_days` para evitar vazamento de labels sobrepostos.
3. **Walk-forward:** repetir a avaliação em múltiplas janelas, por exemplo treino em 24 meses, validação em 6 meses e teste nos 3 meses seguintes, avançando a janela.
4. **Teste final congelado:** depois de escolhido o modelo, rodar uma única avaliação no teste final; se o teste for usado para ajustar decisões, ele deixa de ser teste e vira validação.
5. **Paper trading prospectivo:** somente após teste OOS aprovado; nenhuma otimização retroativa usando o período de paper enquanto ele estiver ativo.

### 13.3 Construção do dataset supervisionado

Cada linha do dataset deve representar um par `(ticker, reference_date)` com features conhecidas até o fechamento de `reference_date` e labels calculadas exclusivamente com dados futuros para fins de treino histórico.

Campos mínimos recomendados:

| Grupo | Campos |
|---|---|
| Chaves | `ticker`, `reference_date`, `valid_for`, `feature_version`, `label_version` |
| OHLCV base | `open`, `high`, `low`, `close`, `volume`, `financial_volume` |
| Features técnicas | retornos, volatilidade, ranges, distância de médias, volume relativo, gaps, máximas/mínimas recentes |
| Features de mercado | retorno do índice de referência, volatilidade agregada, breadth, regime de volume |
| Qualidade | flags de dado ausente, candle suspeito, volume zero, ticker recém-listado |
| Labels | `label_class`, `future_return`, `hit_target`, `hit_stop`, `days_to_event` |

Regras de qualidade do dataset:

- remover ou marcar exemplos com `close <= 0`, volume inexistente, candle duplicado ou data sem pregão;
- exigir histórico mínimo por ativo, por exemplo 252 pregões antes de permitir o ticker no treino;
- winsorizar ou padronizar outliers extremos somente usando estatísticas calculadas no treino;
- persistir o dataset ou seu hash para permitir reprodução exata do treino.

### 13.4 Definição de labels

A label deve refletir a oportunidade operacional do sistema, não apenas se o fechamento subiu ou caiu. Para alinhar modelo e backtest, recomenda-se uma label baseada em barreiras.

Versão inicial sugerida (`label_eod_barrier_v1`):

1. calcular `entry_buy = close(D) * (1 - x_pct)` e `entry_sell = close(D) * (1 + x_pct)`;
2. observar o pregão `valid_for = D+1` para verificar se a entrada seria tocada;
3. se BUY toca entrada em `D+1`, avaliar nos próximos `horizon_days` se target ou stop ocorre primeiro;
4. repetir simetricamente para SELL;
5. classificar:
   - `up`: cenário BUY tem entrada e resultado esperado positivo ou melhor relação retorno/risco;
   - `down`: cenário SELL tem entrada e resultado esperado positivo ou melhor relação retorno/risco;
   - `neutral`: nenhum lado entra, ambos falham ou o retorno esperado não cobre custos e slippage.

Também é útil manter labels auxiliares:

- `future_return_1d`, `future_return_5d`, `future_return_15d`;
- `max_favorable_excursion` e `max_adverse_excursion`;
- `entry_filled_buy`, `entry_filled_sell`;
- `net_return_after_costs`.

### 13.5 Pré-processamento e prevenção de vazamento

- Ajustar `StandardScaler`, normalizadores, imputadores e seleção de features somente no conjunto de treino.
- Aplicar os parâmetros aprendidos em validação, teste e inferência sem recalcular estatísticas globais.
- Features com janelas móveis devem usar apenas dados até `D`, nunca incluir `D+1`.
- Features de ranking cross-sectional podem usar todos os ativos de `D`, mas não podem usar retornos futuros.
- Dividendos, grupamentos e eventos societários devem ser tratados de forma consistente com a origem dos candles.
- Separar scripts de `fit_transform` e `transform` para impedir que pipelines de inferência refaçam treinamento acidentalmente.

### 13.6 Famílias de redes a comparar

O primeiro ciclo deve comparar arquiteturas simples antes de avançar para modelos sequenciais complexos.

| Prioridade | Modelo | Quando usar | Observação |
|---:|---|---|---|
| 1 | MLP tabular | Baseline neural com features agregadas | Simples, rápido, auditável |
| 2 | MLP residual com batch/layer norm | Quando MLP simples underfitar | Melhor estabilidade |
| 3 | 1D CNN temporal | Quando usar janelas OHLCV normalizadas | Captura padrões locais de sequência |
| 4 | LSTM/GRU | Quando houver evidência de dependência temporal longa | Mais risco de overfitting |
| 5 | Transformer temporal pequeno | Somente após dataset robusto | Alto custo e risco de ajuste espúrio |
| 6 | Ensemble neural + heurístico | Quando modelos individuais forem complementares | Pode ser modo `hybrid` |

Manter sempre modelos não neurais de referência, como regressão logística, random forest ou gradient boosting, para garantir que a rede neural realmente agrega valor.

### 13.7 Protocolo de treino

Configuração inicial recomendada:

- função de perda: `cross_entropy` com pesos por classe ou focal loss se houver desbalanceamento forte;
- otimizador: AdamW;
- regularização: dropout, weight decay e early stopping;
- batch: amostragem estratificada por classe e, se necessário, balanceada por data;
- seed: fixar sementes e registrar versões de bibliotecas;
- treino máximo: número alto de épocas com early stopping pela métrica de validação financeira, não apenas loss;
- calibração: aplicar temperature scaling ou isotonic/calibration no conjunto de validação.

Métrica principal para early stopping:

```text
score_validacao = retorno_medio_liquido * profit_factor_ajustado * cobertura_util
```

Onde `cobertura_util` penaliza modelos que geram sinais demais ou sinais de menos. Métricas puramente estatísticas devem ser secundárias.

### 13.8 Otimização de thresholds e seleção operacional

Após treinar o modelo, escolher thresholds em validação e congelar para teste.

Parâmetros a otimizar:

- `min_prob_up` e `min_prob_down`;
- limite máximo de sinais por dia;
- ranking por `confidence`, margem `prob_up - prob_down` ou retorno esperado;
- `x_pct`, `target_pct`, `stop_pct` e `horizon_days`, quando tratados como configuração versionada;
- filtros de liquidez e volatilidade.

A busca deve ser conservadora:

1. limitar o espaço de parâmetros antes de olhar resultados;
2. preferir grades pequenas e interpretáveis;
3. validar por walk-forward;
4. aplicar penalidade para turnover excessivo e concentração por ativo/setor;
5. promover a configuração mais robusta, não a de maior retorno isolado.

### 13.9 Critérios para escolher a melhor rede

A melhor rede não é necessariamente a de maior accuracy. A escolha deve combinar robustez estatística, desempenho financeiro e viabilidade operacional.

Critérios mínimos sugeridos para promoção ao paper trading:

| Dimensão | Critério mínimo |
|---|---|
| Teste OOS | retorno líquido positivo depois de custos e slippage conservador |
| Robustez | desempenho positivo em maioria das janelas walk-forward |
| Drawdown | drawdown compatível com limite de risco definido |
| Profit factor | maior que 1,10 no teste OOS, idealmente 1,20+ antes de paper |
| Amostra | quantidade suficiente de trades executados por lado, evitando conclusão com poucos eventos |
| Calibração | probabilidades monotônicas: faixas de maior confiança devem ter melhor resultado médio |
| Estabilidade | sem dependência extrema de poucos ativos, poucos dias ou um único regime |
| Operação | latência e custo compatíveis com execução diária EOD |

Critérios de bloqueio:

- bom resultado apenas no treino e degradação forte em validação/teste;
- performance concentrada em menos de 5 pregões ou poucos tickers;
- resultados muito sensíveis a pequena mudança de threshold;
- probabilidade mal calibrada, com sinais de alta confiança perdendo mais que baixa confiança;
- diferença relevante entre backtest vetorizado e backtest canônico do projeto.

### 13.10 Período de testes e promoção

Fluxo recomendado:

1. **Backtest interno:** treino + validação + teste OOS com custos conservadores.
2. **Shadow mode:** 20 a 30 pregões gerando apenas `neural_eod_predictions`, sem `sinais_eod` operacionais.
3. **Sinais paralelos controlados:** 60 pregões gravando sinais neurais versionados e comparando com heurístico, sem substituir a produção.
4. **Paper trading completo:** 120 pregões ou até atingir amostra mínima de trades executados definida pelo projeto.
5. **Promoção parcial:** ativar `SIGNAL_SOURCE=hybrid` para pequena fração operacional ou limite reduzido de sinais.
6. **Promoção total:** somente com aprovação explícita, monitoramento diário e rollback para `heuristic`.

Durante todo o período de teste, registrar diariamente:

- quantidade de predições por classe;
- sinais gerados e filtrados;
- trades executados, `NO_FILL`, `TARGET`, `STOP` e `EXPIRE`;
- performance por lado, ativo, setor, regime e faixa de confiança;
- divergências entre inferência, sinais e backtest.

### 13.11 Retreinamento, versionamento e governança

- Criar versões imutáveis para `model_version`, `feature_version`, `label_version` e `training_dataset_snapshot`.
- Retreinar em cadência mensal ou trimestral, mas promover apenas se superar o modelo campeão em teste OOS e paper/shadow.
- Manter estratégia challenger/champion:
  - **champion:** modelo aprovado para sinais;
  - **challenger:** modelo novo rodando em shadow/paper;
  - **rollback:** versão anterior aprovada, pronta para reativação.
- Registrar artefatos: pesos do modelo, configuração, métricas, thresholds, schema de features, hash do dataset e data de treino.
- Bloquear inferência se houver incompatibilidade entre `feature_version` do job e versão esperada pelo modelo.

### 13.12 Entregáveis técnicos do módulo de treino

| Entregável | Objetivo |
|---|---|
| `neural_training_datasets` | Tabela ou partição com dataset supervisionado versionado |
| `neural_model_registry` | Registro de modelos, métricas, thresholds e status (`candidate`, `shadow`, `paper`, `approved`, `rejected`) |
| `neural_training_runs` | Histórico de execuções de treino, parâmetros e artefatos |
| Script/job de dataset | Gera features e labels com split temporal reproduzível |
| Script/job de treino | Treina arquiteturas candidatas e grava métricas |
| Script/job de avaliação | Roda backtest canônico em validação/teste |
| Job de inferência EOD | Gera `neural_eod_predictions` diariamente |
| Dashboard operacional | Compara heurístico, neural e híbrido por período, ativo e versão |

### 13.13 Roadmap prático para iniciar

1. **Semana 1:** criar DDLs de registry/dataset, especificar `feature_version` e `label_version`.
2. **Semana 2:** implementar geração offline do dataset com split temporal e embargo.
3. **Semana 3:** treinar baseline MLP e baselines não neurais; avaliar métricas estatísticas.
4. **Semana 4:** integrar avaliação com o backtest canônico e escolher thresholds em validação.
5. **Semana 5:** rodar teste OOS congelado e selecionar champion inicial ou rejeitar ciclo.
6. **Semana 6:** colocar job de inferência em shadow mode gravando `neural_eod_predictions`.
7. **Semanas 7 a 14:** acompanhar paper/shadow, comparar contra heurístico e decidir promoção parcial.
