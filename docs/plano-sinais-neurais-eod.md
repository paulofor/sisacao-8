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

- Criar DDL da tabela `neural_eod_predictions`.
- Definir schema mínimo de features.
- Definir convenção de `model_id`, `model_version` e `feature_version`.
- Documentar contratos de entrada/saída.

### Fase 2 — Dataset de treino

- Montar dataset histórico por ticker/data.
- Criar labels `up`, `down`, `neutral` usando horizonte e threshold versionados.
- Separar treino/validação/teste em ordem cronológica.
- Evitar vazamento temporal.

### Fase 3 — Treino neural baseline

- Começar com MLP simples.
- Registrar métricas por classe.
- Avaliar matriz de confusão, precisão direcional e cobertura.
- Salvar artefato do modelo com versão.

### Fase 4 — Inferência EOD sem produção

- Criar job `neural_eod_predictions`.
- Rodar diariamente após o fechamento.
- Gravar apenas predições, sem gerar sinais operacionais.
- Validar estabilidade dos outputs por alguns pregões.

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
