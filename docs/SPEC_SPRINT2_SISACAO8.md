# sisacao-8 — Especificação da Sprint 2 (OHLCV Diário + Sinais EOD)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 2  
**Objetivo macro:** evoluir o dado diário para **OHLCV** (a partir do COTAHIST da B3) e entregar um **Gerador de Sinais EOD** (até 22h BRT) com output padronizado e rastreável, respeitando o limite operacional de **até 5 sinais** por dia.

> **Nota:** o sistema **não executa ordens**. Ele publica sinais para execução manual via ordens limitadas.

---

## 1) Contexto (o que já existe da Sprint 1)

A Sprint 1 entregou:
- Coleta intraday via Google Finance (15m) → BigQuery (`cotacao_intraday.cotacao_b3`)
- Coleta diária via arquivo da B3 (COTAHIST) → BigQuery (atualmente “fechamento diário”)
- Lista de tickers ativos via BigQuery (`cotacao_intraday.acao_bovespa`)
- Bloqueio por feriados via BigQuery (`cotacao_intraday.feriados_b3`)

Referência no repositório: `README.md` e funções `google_finance_price` / `get_stock_data`.

---

## 2) Objetivos da Sprint 2

### 2.1 Objetivos técnicos (obrigatórios)
1. Criar (ou evoluir) a base **diária OHLCV** usando o COTAHIST (B3).
2. Tornar a carga diária **idempotente** (reprocessar não duplica).
3. Criar o **Gerador de Sinais EOD** (rodar após fechamento e publicar até 22h BRT).
4. Publicar sinais em BigQuery (tabela `sinais_eod`) com schema fixo.
5. Implementar validações mínimas e logs operacionais.

### 2.2 Entregáveis
- **Nova tabela** diária OHLCV (recomendado: `cotacao_ohlcv_diario`).
- Job/função `generate_signals_eod` (Cloud Run ou Cloud Function) + agendamento.
- Tabela `sinais_eod` com histórico de sinais e campos de rastreabilidade.
- Testes unitários mínimos (parser/normalização e gerador de sinais).

---

## 3) Fonte diária (B3) — campos e layout

Usaremos o arquivo **COTAHIST** (ZIP/TXT) da B3. Os registros de cotações são `TIPREG = "01"` e possuem largura fixa (245 bytes).

### 3.1 Campos essenciais (Registro 01)
Para construir OHLCV diário, extrair pelo menos:

- `DATA DO PREGÃO` (pos 03–10)
- `CODNEG` (ticker) (pos 13–24)
- `PREABE` (abertura) (pos 57–69)
- `PREMAX` (máxima) (pos 70–82)
- `PREMIN` (mínima) (pos 83–95)
- `PREULT` (fechamento/último) (pos 109–121)
- `QUATOT` (quantidade negociada) (pos 153–170)
- `VOLTOT` (volume total negociado) (pos 171–188)
- `TOTNEG` (número de negócios) (pos 148–152)
- `FATCOT` (fator de cotação) (pos 211–217) — importante para normalização de preços

### 3.2 Conversão numérica e fator de cotação
Os campos de preço são do tipo `(11)V99`, ou seja:
- interpretar como inteiro/float e **dividir por 100** para obter o valor com 2 casas.
- aplicar **FATCOT** quando necessário (ex.: alguns ativos podem estar cotados por lote, e não por unidade).

**Regra sugerida (normalização):**
- `preco = (int(preco_str) / 100.0) / max(1, fator_cotacao)`

> A equipe deve confirmar o comportamento em amostras reais (tickers de ações comuns geralmente têm `FATCOT=1`).

### 3.3 Mapeamento de slicing (Python)
As posições do layout são 1-indexed e inclusive. Em Python (0-index), o slicing equivalente é:

- `data_pregao = linha[2:10]`
- `ticker = linha[12:24].strip()`
- `open = linha[56:69]`
- `high = linha[69:82]`
- `low = linha[82:95]`
- `close = linha[108:121]`
- `totneg = linha[147:152]`
- `quatot = linha[152:170]`
- `voltot = linha[170:188]`
- `fatcot = linha[210:217]`

---

## 4) Modelo de dados (Data Contract)

### 4.1 Tabela diária OHLCV (BigQuery)
**Tabela recomendada:** `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario`  
- `PARTITION BY data_pregao`
- `CLUSTER BY ticker`

Campos mínimos:
- `ticker` STRING (REQUIRED)
- `data_pregao` DATE (REQUIRED)
- `open` FLOAT
- `high` FLOAT
- `low` FLOAT
- `close` FLOAT
- `volume` NUMERIC (ou FLOAT)  *(a decidir: usar `voltot` como volume “monetário” e/ou `quatot` como volume “quantidade”)*
- `qtd_negociada` NUMERIC (quatot)
- `num_negocios` INT64 (totneg)
- `fonte` STRING (ex.: `"b3_cotahist"`)
- `atualizado_em` DATETIME (America/Sao_Paulo)

### 4.2 Tabela de sinais EOD
**Tabela recomendada:** `ingestaokraken.cotacao_intraday.sinais_eod`  
- `PARTITION BY date_ref`
- `CLUSTER BY ticker`

Campos mínimos:
- `date_ref` DATE (dia do qual o sinal foi calculado)
- `valid_for` DATE (pregão seguinte)
- `ticker` STRING
- `side` STRING (`"BUY"` ou `"SELL"`)
- `entry` FLOAT
- `target` FLOAT
- `stop` FLOAT
- `x_rule` STRING (ex.: `"close(D)*0.98"`)
- `y_target_pct` FLOAT (ex.: 0.07)
- `y_stop_pct` FLOAT (ex.: 0.07)
- `rank` INT64
- `model_version` STRING (ex.: `"signals_v0"`)
- `created_at` DATETIME (America/Sao_Paulo)

---

## 5) Idempotência (obrigatório)

### 5.1 Diário OHLCV
A carga **não pode duplicar** ao reprocessar o mesmo dia.
Estratégia recomendada:
- carregar em **staging** (tabela temporária/particionada do dia) e executar `MERGE` na tabela final com chave `(ticker, data_pregao)`.

### 5.2 Sinais EOD
Sinais também devem ser idempotentes:
- chave lógica: `(date_ref, ticker, model_version)`
- reprocessamento substitui o registro (MERGE) ou apaga partição do dia e recria.

---

## 6) Gerador de Sinais EOD (Sprint 2: versão V0)

### 6.1 Quando roda
- Em dias de pregão, após fechamento.
- Deve publicar sinais até **22h (America/Sao_Paulo)**.
- Deve **pular feriados** consultando `feriados_b3`.

### 6.2 Regra V0 para X e Y
Para destravar Sprint 2, usar um baseline simples e configurável:

- **BUY:** `X_buy = close(D) * (1 - x_pct)`  
- **SELL:** `X_sell = close(D) * (1 + x_pct)`  

Parâmetros iniciais (config via env):
- `x_pct = 0.02` (2%)
- `target_pct = 0.07` (7%)
- `stop_pct = 0.07` (7%)

Cálculo:
- BUY:
  - `entry = X_buy`
  - `target = entry * (1 + target_pct)`
  - `stop = entry * (1 - stop_pct)`
- SELL:
  - `entry = X_sell`
  - `target = entry * (1 - target_pct)`
  - `stop = entry * (1 + stop_pct)`

### 6.3 Limite operacional (máx 5)
O gerador deve publicar **no máximo 5 sinais** por dia:
- ranking simples recomendado (V0): maior `voltot` (ou maior `quatot`)
- `rank = 1..N` e **cortar em 5**

### 6.4 Output extra opcional
Além do BigQuery, o serviço pode:
- responder um JSON no endpoint HTTP (útil para inspeção)
- opcionalmente gerar CSV/JSON em bucket (não obrigatório na Sprint 2)

---

## 7) Agendamento (Scheduler)

Criar 1 job no Cloud Scheduler para executar o gerador EOD:
- Target: HTTP (Cloud Run ou Cloud Function)
- Auth: OIDC (service account com permissão de invocação)
- Timezone: `America/Sao_Paulo`
- Horário sugerido: 19:00 BRT (com margem até 22h)

> Se o time preferir, pode existir um “Force run” manual para reprocessamento.

---

## 8) Validações e logging (mínimos)

### 8.1 Validações de OHLC
- `high >= max(open, close)`
- `low <= min(open, close)`
- `high >= low`
- `close > 0`
- `volume >= 0` / `qtd_negociada >= 0`

### 8.2 Validações do gerador de sinais
- Não gerar sinais se não existir candle diário do dia D.
- Garantir que `valid_for` seja o próximo **dia de pregão** (não feriado).
- Garantir `target` e `stop` coerentes com `side`.

### 8.3 Logs obrigatórios
- dia processado (`date_ref`), `valid_for`
- tickers lidos, candles válidos
- sinais gerados (N) e sinais publicados (≤ 5)
- motivo de skip (feriado / sem dados / falha download)
- versão do modelo (`model_version`)

---

## 9) Testes (obrigatórios)

### 9.1 Unit tests
- Parser OHLCV:
  - extrai corretamente campos por slicing
  - converte tipos e aplica fator de cotação
- Regras V0 (X/Y) geram `entry/target/stop` corretamente
- Ranking e corte top 5

### 9.2 Integração mínima
- Pipeline de 1 dia:
  1) ingest diário OHLCV
  2) gerar sinais EOD
  3) conferir escrita no BigQuery

---

## 10) Critérios de aceite (Definition of Done)

Sprint 2 está “Pronta” quando:
1. Existe uma tabela diária OHLCV com dados de **pelo menos 3 pregões** recentes.
2. Reprocessar o mesmo pregão **não duplica** (idempotência OK).
3. O gerador EOD publica `sinais_eod` até 22h BRT e nunca publica mais de 5 sinais.
4. Logs permitem diagnosticar problemas sem “falhas silenciosas”.
5. Testes unitários passam no CI.

---

## 11) Riscos e decisões registradas

- Dados da B3 são fornecidos “como estão”, sem ajustes por proventos/inflação.
- `FATCOT` pode exigir normalização; validar com amostras reais.
- Google Finance pode ter “buracos” intraday; Sprint 2 não depende disso para OHLCV/sinais.

---

## 12) Checklist do que o PO deve enviar para a equipe (antes de começar)

- Confirmar nomes finais das tabelas (`cotacao_ohlcv_diario`, `sinais_eod`).
- Confirmar regra V0: `x_pct`, `target_pct`, `stop_pct` (valores iniciais).
- Confirmar critério de ranking (voltot vs quatot).
- Confirmar horário do scheduler (ex.: 19:00 BRT).
- Confirmar se o output adicional (JSON/CSV) será necessário na Sprint 2.

---

## 13) Referências (colocar no README interno / docs)

> (URLs listadas em bloco de código para fácil cópia)

```text
B3 — Cotações históricas (descrição do arquivo e campos):
https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/

B3 — Layout do arquivo COTAHIST (SeriesHistoricas_Layout.pdf):
https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf

BigQuery — DML / MERGE:
https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax

Cloud Scheduler — rodar HTTP com auth / Cloud Run:
https://cloud.google.com/run/docs/triggering/using-scheduler
https://docs.cloud.google.com/scheduler/docs/http-target-auth
```
