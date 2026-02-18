# sisacao-8 — Especificação da Sprint 3 (OHLCV Diário + Sinais EOD V1 + Backtest Diário)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 3  
**Objetivo macro:** transformar a base diária em **OHLCV** (mínimo/máximo do dia incluídos) e entregar um pipeline **EOD → sinais → backtest diário** para testar a tese:

- **BUY (compra):** “Se no pregão seguinte o preço ficar **abaixo de X**, há potencial de subir **Y%**.”  
- **SELL (venda/short opcional):** “Se no pregão seguinte o preço ficar **acima de X**, há potencial de cair **Y%**.”

> **Nota operacional:** entrada/saída serão **manuais** via ordens limitadas. O sistema **não executa ordens**; apenas publica sinais e métricas.

---

## 1) Contexto (baseline após a Sprint 2)

- Intraday 15m via Google Finance → BigQuery (`cotacao_intraday.cotacao_b3`)
- Diário via COTAHIST (B3) → BigQuery (atualmente com foco em **fechamento**)
- Lista de tickers ativos via BigQuery (`cotacao_intraday.acao_bovespa`)
- Bloqueio por feriados via BigQuery (`cotacao_intraday.feriados_b3`)

---

## 2) Objetivos da Sprint 3

### 2.1 Objetivos técnicos (obrigatórios)
1. Evoluir o diário para **OHLCV** usando o **COTAHIST da B3** (com mínimo e máximo do dia).
2. Implementar carga **idempotente** no BigQuery (MERGE com chave `(ticker, data_pregao)`).
3. Implementar **Gerador de Sinais EOD (V1)**:
   - roda após o fechamento e publica até **22h (America/Sao_Paulo)**
   - gera **sinais de entrada** para o pregão seguinte
   - respeita o limite operacional: **máximo 5 sinais** por dia
4. Implementar **Backtest Diário** para a tese usando apenas **dados diários** (LOW/HIGH):
   - valida “tocou a entrada?”
   - simula target/stop em janela **N dias** usando máximas/mínimas diárias
   - produz métricas e score para ranking de sinais
5. Documentar parâmetros e contratos (tabelas, schemas, env vars, regras).

### 2.2 Entregáveis
- Tabela `cotacao_ohlcv_diario` (BigQuery) populada e validada.
- Função/serviço `generate_signals_eod` + job de agendamento.
- Tabela `sinais_eod` (BigQuery) com histórico.
- Script/serviço `backtest_daily` + tabelas de resultados (`backtest_trades`, `backtest_metrics`).
- Testes unitários mínimos e docs.

---

## 3) Fonte diária (B3) e premissas

### 3.1 Fonte
Usar **COTAHIST** da B3 (zip + txt) e seu layout oficial. A B3 destaca que o arquivo contém preços (abertura, mínimo, máximo, fechamento), negócios e volume; e que os dados **não vêm ajustados por inflação/proventos** (importante para análise).  
**Referência:** página “Cotações históricas” e “Layout do arquivo”.  
- https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/  
- https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf

### 3.2 Campos que vamos extrair (mínimo necessário)
Para cada ticker/dia:
- data do pregão
- abertura (open)
- máxima (high)
- mínima (low)
- fechamento (close)
- quantidade negociada (qtd)
- volume financeiro (vol)
- número de negócios (trades)
- fator de cotação (fatcot) (para normalização quando aplicável)

---

## 4) Modelo de dados (Data Contract)

### 4.1 Tabela OHLCV Diário
**Tabela:** `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`  
**Particionamento:** `PARTITION BY data_pregao`  
**Clustering:** `CLUSTER BY ticker`

Campos:
- `ticker` STRING (REQUIRED)
- `data_pregao` DATE (REQUIRED)
- `open` FLOAT
- `high` FLOAT
- `low` FLOAT
- `close` FLOAT
- `qtd_negociada` NUMERIC
- `volume_financeiro` NUMERIC
- `num_negocios` INT64
- `fatcot` INT64
- `fonte` STRING (ex.: `b3_cotahist`)
- `atualizado_em` DATETIME (America/Sao_Paulo)

> **Compat:** manter `cotacao_fechamento_diario` por enquanto (opcional), mas o sistema deve passar a depender de `cotacao_ohlcv_diario` para sinais e backtest.

### 4.2 Tabela de sinais EOD
**Tabela:** `ingestaokraken.cotacao_intraday.sinais_eod`  
**Particionamento:** `PARTITION BY date_ref`  
**Clustering:** `CLUSTER BY ticker`

Campos mínimos:
- `date_ref` DATE (dia D usado no cálculo)
- `valid_for` DATE (pregão seguinte)
- `ticker` STRING
- `side` STRING (`BUY` | `SELL`)
- `entry` FLOAT (X)
- `target` FLOAT
- `stop` FLOAT
- `x_rule` STRING (descrição da regra e parâmetros)
- `y_target_pct` FLOAT (ex.: 0.07)
- `y_stop_pct` FLOAT (ex.: 0.07)
- `horizon_days` INT64 (janela N do backtest)
- `ranking_key` STRING (ex.: `score_v1`)
- `score` FLOAT (0–1 ou escala definida)
- `rank` INT64
- `model_version` STRING (ex.: `signals_v1`)
- `created_at` DATETIME (America/Sao_Paulo)

### 4.3 Tabelas do backtest (novas)
**Tabela 1:** `ingestaokraken.cotacao_intraday.backtest_trades`  
- 1 linha por “trade simulado” (quando a entrada é tocada).

Campos:
- `date_ref` DATE
- `valid_for` DATE
- `ticker` STRING
- `side` STRING
- `entry` FLOAT
- `target` FLOAT
- `stop` FLOAT
- `horizon_days` INT64
- `entry_hit` BOOL
- `entry_fill_date` DATE (data em que tocou a entrada)
- `exit_date` DATE (data do alvo/stop/expiração)
- `exit_reason` STRING (`TARGET` | `STOP` | `EXPIRE`)
- `exit_price` FLOAT (preço considerado)
- `return_pct` FLOAT
- `mfe_pct` FLOAT (max favorable excursion - usando highs/lows diários)
- `mae_pct` FLOAT (max adverse excursion)
- `created_at` DATETIME

**Tabela 2:** `ingestaokraken.cotacao_intraday.backtest_metrics`  
- métricas agregadas por ticker e/ou global.

Campos:
- `as_of_date` DATE (data de atualização)
- `ticker` STRING (NULL para global)
- `side` STRING (ou NULL)
- `horizon_days` INT64
- `signals` INT64
- `fills` INT64
- `win_rate` FLOAT
- `avg_return` FLOAT
- `avg_win` FLOAT
- `avg_loss` FLOAT
- `profit_factor` FLOAT
- `avg_days_in_trade` FLOAT
- `created_at` DATETIME

---

## 5) Idempotência (obrigatório)

### 5.1 Diário OHLCV (MERGE)
A carga diária deve ser **idempotente**:
- staging (tabela temporária ou partição do dia)
- `MERGE` na tabela final usando chave `(ticker, data_pregao)`

**Referência BigQuery MERGE:**  
https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax

### 5.2 Sinais e backtest
- `sinais_eod`: chave `(date_ref, ticker, model_version)`  
- `backtest_trades`: chave sugerida `(date_ref, ticker, side, model_version, horizon_days)`  
- reprocessamento deve substituir/atualizar, não duplicar.

---

## 6) Gerador de Sinais EOD (V1) — regra e ranking

### 6.1 Quando roda
- Em dias de pregão (não feriado e não fim de semana)
- Após o fechamento, publica até **22:00 (America/Sao_Paulo)**
- Calcula `valid_for` como **próximo pregão** (pular feriado + fim de semana)

### 6.2 Regra V1 (tese X/Y) — baseline configurável
**Parâmetros (env ou tabela de config):**
- `X_MODE = "PCT_FROM_CLOSE" | "ATR" | "PIVOT"` *(Sprint 3 começa com PCT_FROM_CLOSE)*
- `x_pct` (ex.: 0.02)
- `target_pct` (Y, ex.: 0.07)
- `stop_pct` (ex.: 0.07)
- `horizon_days` (N, ex.: 10)
- `max_signals_per_day = 5`
- `min_liquidez_rank` (opcional)

**Baseline (PCT_FROM_CLOSE):**
- BUY: `entry = close(D) * (1 - x_pct)`
- SELL: `entry = close(D) * (1 + x_pct)`

**Target/Stop (sempre pré-definidos):**
- BUY:
  - `target = entry * (1 + target_pct)`
  - `stop = entry * (1 - stop_pct)`
- SELL:
  - `target = entry * (1 - target_pct)`
  - `stop = entry * (1 + stop_pct)`

> **Short opcional:** se a operação SELL não for desejada no início, manter `ALLOW_SELL=false` e publicar apenas BUY.

### 6.3 Ranking e corte para 5 sinais
Na Sprint 3, o ranking deve ser **explicável** (sem ML pesado ainda). Proposta:

**score_v1 = combinação ponderada**
- `score_backtest` (win_rate e profit_factor recentes)
- `score_liquidez` (volume_financeiro médio recente)
- `penalidade_volatilidade` (evitar ativos com gaps extremos)

Exemplo (simplificado):
- `score = 0.6 * win_rate_rolling + 0.4 * normalize(log(volume_medio))`

Cortar:
- ordenar por `score desc`
- publicar no máximo `max_signals_per_day` (5)

---

## 7) Backtest Diário (Sprint 3: obrigatório)

### 7.1 Por que diário
O usuário definiu que:
- entradas/saídas serão validadas por **mínimo e máximo do dia** (dados diários),
- intraday 15m existe, mas **não é a base do backtest** nesta fase.

### 7.2 Lógica do backtest (conservadora)
Para cada sinal publicado em `sinais_eod`:

**1) Verificar se tocou a entrada no dia `valid_for`:**
- BUY: `low(valid_for) <= entry`
- SELL: `high(valid_for) >= entry`
Se não tocar: `entry_hit = false` e não gera trade simulado (ou gera com exit_reason = `NO_FILL`, a decidir).

**2) Se tocou a entrada, simular evolução por até N dias:**
Para cada dia a partir do `entry_fill_date` até `horizon_days`:
- BUY:
  - se `low <= stop` → STOP (assumir stop executado)
  - senão se `high >= target` → TARGET
- SELL:
  - se `high >= stop` → STOP
  - senão se `low <= target` → TARGET

**3) Empate (stop e target no mesmo dia)**
Como não temos intraday, definir regra determinística (pior caso):
- BUY: se `low <= stop` e `high >= target` no mesmo dia → considerar `STOP` (conservador).
- SELL: se `high >= stop` e `low <= target` no mesmo dia → considerar `STOP`.

**4) Expiração**
Se não bater target/stop até N dias:
- `exit_reason = EXPIRE`
- `exit_price = close(dia_final)`
- calcular retorno.

### 7.3 Métricas
Gerar pelo menos:
- `win_rate`, `profit_factor`, `avg_return`, `avg_days_in_trade`
- por ticker, por side e global
- janela rolling (ex.: últimos 60 pregões) para ranking

---

## 8) Agendamento / execução

### 8.1 Serviços
- `get_stock_data` (diário) continua rodando como hoje
- `generate_signals_eod` (novo) roda 1x por pregão
- `backtest_daily` (novo) pode rodar logo após `generate_signals_eod` ou em horário separado

### 8.2 Cloud Scheduler (HTTP + OIDC)
- Target: Cloud Run (recomendado) ou Cloud Function
- Auth: OIDC com service account
- Timezone: `America/Sao_Paulo`

Referências:
- Cloud Scheduler HTTP auth: https://cloud.google.com/scheduler/docs/http-target-auth  
- Rodar Cloud Run via Scheduler: https://cloud.google.com/run/docs/triggering/using-scheduler

---

## 9) Validações e logging (mínimos)

### 9.1 Validações OHLCV
- `high >= low`
- `high >= max(open, close)`
- `low <= min(open, close)`
- `close > 0`
- `qtd_negociada >= 0`, `volume_financeiro >= 0`

### 9.2 Validações sinais/backtest
- `valid_for` deve ser próximo pregão (não feriado/fim de semana)
- `target/stop` coerentes com `side`
- `rank` ≤ 5 e único no dia

### 9.3 Logs obrigatórios (por execução)
- `date_ref`, `valid_for`
- tickers processados, candles válidos e rejeitados
- sinais gerados (N) e publicados (≤ 5)
- trades simulados (fills) e métricas
- motivo de skip (feriado / sem dados / falha download)

---

## 10) Testes (obrigatórios)

### 10.1 Unit tests
- Parser COTAHIST OHLCV (slicing + conversão numérica)
- Função “próximo pregão” (considerando feriados e fim de semana)
- Regras de entrada/target/stop e tie-break (pior caso)
- Ranking e corte top 5
- Idempotência: `MERGE` não duplica (testável com dataset de teste/mock)

### 10.2 Integração mínima (1 dia)
1) ingest diário OHLCV
2) gerar sinais EOD
3) rodar backtest para sinais anteriores
4) conferir escrita nas tabelas

---

## 11) Critérios de aceite (Definition of Done)

Sprint 3 está pronta quando:
1. `cotacao_ohlcv_diario` tem OHLCV correto para **pelo menos 30 pregões** (amostra) e passa validações.
2. Reprocessamento do mesmo pregão não duplica (idempotência OK).
3. `generate_signals_eod` publica `sinais_eod` até 22h BRT e **nunca publica mais de 5 sinais**.
4. `backtest_daily` gera `backtest_trades` e `backtest_metrics` com lógica documentada e determinística.
5. Testes unitários passam no CI e logs são suficientes para auditoria.

---

## 12) Fora de escopo (para evitar “scope creep”)
- Sentimento de notícias (Reuters, etc.)
- Modelos avançados (LSTM/Transformers) para previsão
- Execução automática de ordens
- Ajuste por proventos no preço (split/dividend) *(pode virar Sprint futura)*

---

## 13) Checklist (PO → equipe)
- Confirmar se **SELL/short** entra na Sprint 3 (`ALLOW_SELL=true/false`)
- Definir parâmetros iniciais: `x_pct`, `target_pct`, `stop_pct`, `horizon_days`
- Definir critério de liquidez (volume_financeiro vs qtd_negociada)
- Definir horários do Scheduler (ex.: 19:00 sinais; 19:10 backtest)
- Confirmar nomes finais das tabelas e datasets

---

## 14) Referências (para docs internas)
```text
B3 — Cotações históricas (descrição do arquivo e campos):
https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/

B3 — Layout do COTAHIST (SeriesHistoricas_Layout.pdf):
https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf

BigQuery — MERGE / DML:
https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax

Cloud Scheduler — HTTP Auth (OIDC):
https://cloud.google.com/scheduler/docs/http-target-auth

Cloud Run — rodar serviços em agenda (Scheduler):
https://cloud.google.com/run/docs/triggering/using-scheduler
```
