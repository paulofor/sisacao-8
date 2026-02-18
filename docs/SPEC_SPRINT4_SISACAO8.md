# sisacao-8 — Especificação da Sprint 4 (Operação, Observabilidade e Reprodutibilidade)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 4  
**Objetivo macro:** tornar o sistema **operável todos os dias** (sem “mão na massa” manual), com **deploy completo**, **agendamentos confiáveis**, **observabilidade (logs/alertas)**, **checagens de qualidade de dados**, e **infra reproduzível** (ambiente “sobe do zero”).

> **Nota:** esta sprint é “produção/operacional”. Não é sprint de estratégia/ML.  
> O sistema continua **gerando sinais** para execução **manual** com limite operacional de **até 5 ativos**.

---

## 1) Contexto (baseline após a Sprint 3)

O pipeline já possui:
- Intraday 15m (Google Finance) + consolidações (15m/1h)
- Diário oficial via COTAHIST (B3) → OHLCV diário
- Sinais EOD + backtest diário + métricas
- Tabela de feriados e bloqueio por feriados
- Deploy parcial via GitHub Actions para parte das funções/serviços

Nesta Sprint 4, o foco é garantir que:
1) Tudo que roda no dia-a-dia tenha **scheduler**, **deploy**, **monitoramento**, **alerta** e **runbook**;
2) Um novo membro consiga subir o ambiente do zero (infra como código).

---

## 2) Objetivos da Sprint 4

### 2.1 Objetivos técnicos (obrigatórios)
1. **Infra como código (IaC leve):** scripts SQL versionados para criação de *todas* as tabelas/datasets necessários (incluindo tabelas base “raw” e tabelas de configuração).
2. **CI/CD completo:** workflow(s) de deploy para **todas** as funções/serviços/jobs usados em produção.
3. **Agendamento confiável:** Cloud Scheduler com autenticação (OIDC/OAuth) para todos os jobs relevantes (intraday, diário, EOD, backtest, DQ checks).
4. **Observabilidade:** logs estruturados + métricas/alertas para falhas e para “silêncio” (ex.: não gerou sinais; não entrou dado diário; intraday parou).
5. **Qualidade de dados (DQ):** checagens diárias automáticas e persistência do resultado (e alertas).
6. **Operação/Runbook:** documentação de incidentes e procedimento de reprocessamento (idempotente).

### 2.2 Entregáveis
- Diretório `infra/` completo com SQL para:
  - datasets
  - tabelas BigQuery (raw + processadas + sinais + backtest + DQ)
  - views úteis para operação/painel
- Workflows de GitHub Actions (deploy) cobrindo todos os componentes.
- Jobs do Cloud Scheduler criados e documentados (com timezone `America/Sao_Paulo`).
- Alertas configurados (log-based e/ou metrics-based) e documentação do que cada alerta significa.
- Documentação operacional (“runbook”) e checklist diário do operador.

---

## 3) Definição de “produção” para este projeto

Um dia está “OK” quando:
- Intraday (15m) tem dados recentes para tickers ativos (sem buracos grandes)
- Diário OHLCV do último pregão foi gravado
- Sinais EOD foram gerados até 22h BRT (máximo 5)
- Backtest e métricas foram atualizados
- Nenhum alerta de falha (ou falha foi tratada e reprocessada)

---

## 4) Infra como código (BigQuery)

### 4.1 Datasets e tabelas (obrigatório)
Garantir que existam SQLs versionados para criação de:
- **Config/Tickers**
  - `acao_bovespa` (lista de tickers + flag ativo)
  - (opcional) `parametros_estrategia` (x_pct, target_pct, stop_pct, horizon, allow_sell, max_signals)
- **Calendário**
  - `feriados_b3` (ano corrente + próximos anos)
- **Raw/Processado**
  - `cotacao_b3` (raw intraday)
  - `candles_intraday_15m` / `candles_intraday_1h`
  - `cotacao_ohlcv_diario`
- **Sinais e Backtest**
  - `sinais_eod`
  - `backtest_trades`
  - `backtest_metrics`
- **Data Quality**
  - `dq_checks_daily`
  - `dq_incidents` (opcional)

### 4.2 Particionamento e clustering (recomendado)
- Particionar por data (`DATE`) e clusterizar por `ticker` nas tabelas fact (diário, sinais, backtest).
- Motivo: melhora performance/custo e mantém organização de dados dentro das partições (BigQuery reclustering automático).  
  Referência (clustering): https://cloud.google.com/bigquery/docs/clustered-tables

---

## 5) CI/CD completo (GitHub Actions)

### 5.1 Meta
Todos os componentes executáveis devem ter pipeline de deploy automatizado.

**Cobertura esperada (exemplo):**
- `google_finance_price` (Cloud Run)
- `intraday_candles` (Cloud Run Job ou Cloud Run Service)
- `get_stock_data` (Cloud Function ou Cloud Run Job)
- `generate_signals_eod` (Cloud Run Job ou Cloud Run Service)
- `backtest_daily` (Cloud Run Job)
- (opcional) `alerts` / `dq_checks` (Cloud Run Job)

### 5.2 Requisitos de deploy
- Ambiente controlado por variáveis (env vars)
- Secrets fora do repositório (GitHub Secrets / Secret Manager)
- Permissões mínimas por service account (least privilege)
- Tag/versão de imagem e `model_version` rastreável (commit SHA)

---

## 6) Agendamentos (Cloud Scheduler)

### 6.1 Regras
- Timezone: `America/Sao_Paulo`
- Scheduler deve autenticar chamadas HTTP com token (OIDC preferencial para targets que não são Google APIs).  
  Referência (OIDC/OAuth em HTTP targets): https://docs.cloud.google.com/scheduler/docs/http-target-auth

### 6.2 Agenda sugerida (ajustável)
1) **Intraday 15m**  
   - A cada 15 minutos dentro do pregão (ou a cada 15m o dia todo, mas filtrando horário de mercado)
2) **Intraday candles (15m/1h)**  
   - A cada 15 min (ou 1x por hora)
3) **Diário OHLCV (COTAHIST)**  
   - 1x no fim do dia (ou no início do dia seguinte com lookback)
4) **EOD sinais**  
   - 1x após fechamento, garantindo publicação até 22h
5) **Backtest diário**  
   - 1x logo após geração de sinais (ou em seguida ao diário)
6) **DQ checks**  
   - 1x ao final do pipeline (no mesmo dia)

### 6.3 Cloud Run Jobs (recomendado para “tarefas”)
Para jobs batch (EOD/backtest/DQ), preferir Cloud Run Jobs com execução agendada.  
Referência (executar Jobs em agenda): https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule

---

## 7) Observabilidade (Logs, métricas, alertas)

### 7.1 Logs estruturados (obrigatório)
Padronizar logs com:
- `job_name`
- `run_id` (UUID)
- `date_ref` / `valid_for`
- `status` (`STARTED`/`OK`/`WARN`/`ERROR`)
- contagens: tickers processados, linhas inseridas, sinais gerados etc.
- `error_code` / `exception` (quando falhar)

### 7.2 Alertas (obrigatório)
Configurar alertas no Cloud Monitoring, preferencialmente por:
- **log-based alerts**: dispara quando aparecer log “ERROR”/padrão específico
- **log-based metrics**: contagem de erros por janela, para evitar spam

Referências:
- Visão geral de alertas: https://docs.cloud.google.com/monitoring/alerts  
- Monitorar logs / logs-based alerting: https://docs.cloud.google.com/logging/docs/alerting/monitoring-logs  
- Configurar log-based alerts: https://docs.cloud.google.com/logging/docs/alerting/log-based-alerts

### 7.3 Casos de alerta mínimos
1) **Falha de execução** (exceção / status != OK)
2) **Pipeline silencioso**:
   - diário não atualizou no último pregão
   - EOD não gerou sinal até 22h
   - intraday não recebeu pontos por X minutos
3) **Anomalias**:
   - duplicidade acima de threshold
   - volume = 0 para muitos ativos
   - OHLC inválido (high < low etc.)

### 7.4 Painel (dashboard)
Criar um painel simples:
- status do dia (diário, intraday, EOD, backtest)
- top 5 sinais do dia
- última atualização por tabela

Pode ser Looker Studio ou consultas salvas no BigQuery.

---

## 8) Data Quality (DQ) — checagens automáticas

### 8.1 Tabela `dq_checks_daily`
Registrar 1 linha por check:
- `check_date`
- `check_name`
- `status` (`PASS`/`WARN`/`FAIL`)
- `details` (JSON/text)
- `created_at`

### 8.2 Checks mínimos
- **Freshness (diário):** existe OHLCV do último pregão para >= X% dos tickers ativos
- **Freshness (intraday):** último ponto por ticker dentro de janela aceitável
- **Uniqueness:** sem duplicidade por chave lógica
- **OHLC validity:** invariantes `high >= low`, etc.
- **Sinais:** no máximo 5 e todos com `target/stop` coerentes
- **Backtest:** métricas atualizadas (as_of_date)

### 8.3 Ações em FAIL
- Criar incidente (linha em `dq_incidents`) + disparar alerta

---

## 9) Operação e Runbook

### 9.1 Documentos obrigatórios
- `RUNBOOK.md` com:
  - como checar status do dia (queries prontas)
  - como reprocessar um dia (idempotente)
  - como lidar com falha de download COTAHIST
  - como lidar com “buraco” de intraday
  - como interpretar alertas e encerrar incidente

### 9.2 Procedimento de reprocessamento (padrão)
- Reprocessar diário OHLCV para `date_ref` usando lookback
- Regerar sinais EOD para `date_ref`
- Reexecutar backtest e métricas
- Confirmar DQ PASS

---

## 10) Critérios de aceite (Definition of Done)

Sprint 4 está pronta quando:
1) Um ambiente novo consegue ser “subido” usando `infra/` + README (sem dependências implícitas).
2) Todos os jobs em produção estão com:
   - deploy automatizado (CI/CD)
   - scheduler configurado
   - logs padronizados
3) Existem alertas para:
   - falha de execução
   - pipeline silencioso
   - anomalias críticas de dados
4) Existe `RUNBOOK.md` e processo de reprocessamento validado em um dia real.
5) DQ checks rodam diariamente e gravam resultados em `dq_checks_daily`.

---

## 11) Fora de escopo (para evitar “scope creep”)
- Sentimento de notícias (Reuters etc.)
- Modelos avançados de ML/NN para previsão
- Execução automática de ordens (broker)
- Ajuste por proventos/splits (pode ser Sprint futura)
- Otimização sofisticada de parâmetros (grid search/auto-ML)

---

## 12) Checklist (PO → equipe)
- Confirmar padrão de **ambientes** (`dev`, `staging`, `prod`) e nomes de datasets/tabelas
- Confirmar horários do Scheduler (principalmente EOD até 22h)
- Confirmar canais de alerta (email, Slack, etc.)
- Confirmar quais jobs serão Cloud Run Jobs vs Services

---

## 13) Referências (para docs internas)

> URLs em bloco de texto para fácil cópia:

```text
Cloud Scheduler — autenticação HTTP (OIDC/OAuth):
https://docs.cloud.google.com/scheduler/docs/http-target-auth

Cloud Run — executar Jobs em agenda (Scheduler):
https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule

Cloud Monitoring — visão geral de alertas:
https://docs.cloud.google.com/monitoring/alerts

Cloud Logging — monitorar logs e alertar:
https://docs.cloud.google.com/logging/docs/alerting/monitoring-logs
https://docs.cloud.google.com/logging/docs/alerting/log-based-alerts

BigQuery — MERGE / DML:
https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax

BigQuery — clustering:
https://cloud.google.com/bigquery/docs/clustered-tables

B3 — calendário e horários especiais (exemplo 2026):
https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm
```
