# sisacao-8 — Especificação da Sprint 1 (Base de Dados + Sinais EOD)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 1  
**Objetivo macro:** consolidar dados (diário + intraday 15m) e entregar um gerador de sinais EOD (até 22h BRT) com saída padronizada e rastreável.

---

## 1) Contexto do produto (o que estamos construindo)

Este sistema **não executa ordens automaticamente**. Ele gera **sinais objetivos** no **fechamento do dia (EOD)** para que a operação seja feita **manualmente** via **ordens limitadas** no pregão seguinte.

### Regras de operação (MVP)
- **Não é day trade.** O trade pode durar dias/semanas; só será “no mesmo dia” se o preço atingir alvo/stop por acaso.
- **Entrada:** ordem limitada no dia seguinte, condicionada ao preço atingir **X**.
- **Saída:** alvo e stop são **pré-definidos** antes da entrada (ex.: +7% / -7%).
- **Capacidade humana:** **máximo 5 ativos simultâneos** (nesta sprint, isso pode ser apenas uma regra de seleção/ranking dos sinais; controle de posições fica para sprint posterior).

---

## 2) Objetivos da Sprint 1

### 2.1 Objetivos técnicos (obrigatórios)
1. **Padronizar** schema de dados (diário e intraday 15m) para OHLCV.
2. Implementar parser/ingestão confiável do **arquivo diário da B3**.
3. Consolidar a coleta intraday (15m) já existente e garantir consistência/qualidade.
4. Criar o **Job EOD** que gera sinais até **22h (America/Sao_Paulo)**.
5. Garantir **idempotência** e **auditoria** (reprocessar o mesmo dia não duplica e mantém rastreabilidade).

### 2.2 Entregáveis
- Tabelas/datasets com candles diários e intraday (15m) padronizados.
- Processo/rotina EOD rodando por agendamento.
- Saída diária de sinais em **tabela** e/ou **arquivo JSON/CSV**.
- Logs e validações (missing data, duplicidades, feriados/sem pregão, etc.).
- Testes automatizados (parser B3 + validações essenciais).

---

## 3) Fontes de dados e limitações

### 3.1 Diário (B3 – Série histórica de cotações)
- Fonte: arquivos de “cotações históricas” (zip/txt) da B3.
- **Limitação importante:** os preços são fornecidos **sem ajuste por inflação ou proventos** (dividendos, bonificações etc.).  
  Isso impacta comparações de níveis e retornos em datas de eventos corporativos.

### 3.2 Intraday (Google Finance)
- Coleta a cada **15 minutos**.
- Nesta Sprint 1, intraday é **armazenado e validado**; a lógica de backtest/execução ainda não depende dele.

### 3.3 Calendário de negociação (pregão vs feriados)
- Rotinas devem respeitar feriados e **horários especiais** (ex.: Quarta-feira de Cinzas).
- A geração de sinais deve ocorrer após o fechamento do mercado e estar disponível **até 22h BRT**.

---

## 4) Contrato de dados (Data Contract)

### 4.1 Convenções gerais
- Timezone: `America/Sao_Paulo`
- Chave primária de candle: `(ticker, datetime)`  
  - **Diário:** `datetime` = data do pregão (00:00:00 BRT ou campo `date` separado)
  - **Intraday:** `datetime` em BRT ou UTC + campo explícito de timezone (definir padrão no código)

### 4.2 Schema mínimo (OHLCV)
Campos obrigatórios:
- `ticker` (string, ex: PETR4)
- `datetime` (timestamp)
- `open` (float/decimal)
- `high` (float/decimal)
- `low` (float/decimal)
- `close` (float/decimal)
- `volume` (int/decimal)
- `source` (enum: `B3_DAILY`, `GOOGLE_FINANCE_15M`)
- `ingested_at` (timestamp)
- `data_quality_flags` (array/string opcional)

### 4.3 Regras de qualidade (mínimas)
- `high >= max(open, close)` e `low <= min(open, close)`
- `high >= low`
- `volume >= 0`
- Sem duplicidade para `(ticker, datetime, source)`
- Em dias sem pregão (feriados), **não gerar candle diário** e **não gerar sinal**.

---

## 5) Agregação intraday (opcional na Sprint 1)

### 5.1 15m → 1h (se implementarem utilitário)
Viável e recomendado como utilitário (mesmo que não usado no sinal ainda):
- `open = first(open)`
- `high = max(high)`
- `low = min(low)`
- `close = last(close)`
- `volume = sum(volume)`

**Observação:** a agregação deve respeitar o calendário de pregão (janelas corretas).

---

## 6) Motor de sinais EOD (Sprint 1: versão V0)

### 6.1 Quando roda
- Diariamente em dia útil de pregão, após a consolidação do candle diário.
- Deve terminar e publicar os sinais **até 22h BRT**.

### 6.2 O que gera (saída)
Um conjunto de sinais objetivos para o pregão seguinte.

#### Formato sugerido (JSON)
```json
{
  "date_ref": "YYYY-MM-DD",
  "valid_for": "YYYY-MM-DD",
  "model_version": "X_rule_v0",
  "signals": [
    {
      "ticker": "PETR4",
      "side": "BUY",
      "entry": 43.00,
      "target": 46.01,
      "stop": 39.99,
      "reason": "close(D) * 0.98",
      "created_at": "YYYY-MM-DDTHH:MM:SS-03:00"
    }
  ]
}
```

### 6.3 Definição de X e Y (V0, simples para destravar)
- Compra condicional:
  - `X_buy = close(D) * 0.98`
- Venda condicional:
  - `X_sell = close(D) * 1.02`
- Alvo/Stop (fixos no MVP):
  - `target = entry * 1.07` (para BUY) / `entry * 0.93` (para SELL)
  - `stop = entry * 0.93` (para BUY) / `entry * 1.07` (para SELL)

> **Nota:** ajustes finos e otimizações ficam para sprints posteriores. Aqui o foco é padronização, rastreabilidade e execução do pipeline.

---

## 7) Seleção e limite operacional (máximo 5 ativos)

Nesta Sprint 1, implementar pelo menos uma destas abordagens:
- **Opção A (mais simples):** gerar sinais para todos e incluir um campo `rank`, depois o usuário escolhe manualmente.
- **Opção B (recomendado):** já limitar a saída a **top 5** por um critério simples (ex.: volume diário, volatilidade diária, ou liquidez aproximada).

---

## 8) Logging, auditoria e idempotência

### 8.1 Logs mínimos
- Início/fim de execução de cada job (daily ingest, intraday ingest, EOD signals).
- Quantidade de candles lidos/gravados por ticker.
- Quantidade de sinais gerados.
- Avisos: ausência de dados, ticker inválido, feriado/sem pregão, inconsistência OHLC.

### 8.2 Idempotência
- Reexecutar o job do mesmo dia **não deve duplicar registros**.
- Preferir `MERGE`/upsert (ou deletar partição do dia e recriar).

### 8.3 Auditoria / rastreabilidade
- `model_version`
- `source_snapshot` (hash opcional do arquivo B3 do dia)
- `created_at`
- `code_version` (commit hash opcional)

---

## 9) Testes (obrigatórios)

### 9.1 Testes unitários
- Parser do arquivo diário da B3:
  - lê registros e campos conforme layout
  - valida datas e valores
- Validações OHLCV (invariantes)
- Geração de sinais (X_rule_v0)

### 9.2 Testes de integração
- Pipeline “fim a fim” em um dia específico:
  1) ingest diário
  2) ingest intraday
  3) geração EOD
  4) saída publicada

---

## 10) Critérios de aceite (Definition of Done)

A Sprint 1 está “Pronta” quando:
1. Em **3 dias de teste** (datas distintas), o pipeline gerou candles e sinais sem falhas silenciosas.
2. Reprocessar o mesmo dia é idempotente.
3. Existe output diário de sinais (tabela/arquivo) com schema fixo.
4. Logs mostram claramente o que foi ingerido, validado e publicado.
5. Parser do diário da B3 possui testes automatizados e passa em CI.

---

## 11) Riscos e decisões (registrar no repositório)

- **Dados diários B3 não são ajustados** por proventos/inflação → impactos na consistência de níveis e retornos.
- Rotinas dependem de calendário/horários especiais.
- Intraday de Google Finance pode ter limitações de disponibilidade/latência (tratar “buracos”).
- Sprint 1 **não valida estratégia** (sem backtest ainda). Ela prepara o terreno para a Sprint 2.

---

## 12) Comunicação para o time (o que você deve enviar)

**Envie junto deste documento:**
- Lista de tickers-alvo e fonte dessa lista (tabela existente no projeto).
- Padrão de timezone e formato de data/hora no armazenamento.
- Definição final do output (JSON vs tabela) para integração com o seu fluxo manual.
- Ambiente e credenciais (GCP, BigQuery, Cloud Functions/Jobs, etc.) e como rodar local.
- Convenção de versionamento (`model_version`, `code_version`).

---

## 13) Referências (para implementação e validação de fontes)

- B3 — Cotações históricas (explica download e **aviso de não-ajuste por proventos/inflação**)  
- B3 — Layout de interpretação do arquivo (SeriesHistoricas_Layout.pdf)  
- B3 — Calendário de negociação / feriados e horários especiais  
- pandas — `resample().ohlc()` para agregação OHLC  
- Observação sobre vieses comuns em backtest (look-ahead bias / survivorship bias)

