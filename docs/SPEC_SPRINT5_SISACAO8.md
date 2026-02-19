# sisacao-8 — Especificação da Sprint 5 (Hardening: Segurança, Alertas como Código e “Zero-Silêncio”)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 5  
**Objetivo macro:** fechar o ciclo de “produção de verdade” com **segurança (endpoints privados)**, **alertas como código**, **detecção de silêncio (pipelines parados)** e **configuração centralizada por tabela**, reduzindo risco operacional e custo.

> Esta sprint não muda a estratégia de trade. O foco é **confiabilidade + segurança + operação**.

---

## 1) Contexto (baseline após a Sprint 4)

O projeto já possui:
- ingest intraday (Google Finance) + candles (15m/1h)
- ingest diário (COTAHIST) + OHLCV diário
- sinais EOD (top 5) + backtest diário + métricas
- DQ checks + runbook + views de status
- CI/CD e scheduler (parcial/total dependendo do ambiente)

Nesta Sprint 5 vamos “endurecer” (hardening) o stack.

---

## 2) Objetivos da Sprint 5

### 2.1 Objetivos técnicos (obrigatórios)
1. **Segurança:** remover invocação pública desnecessária (`allow-unauthenticated`) e garantir que **apenas Scheduler/SA** consiga executar jobs.
2. **Least privilege:** service accounts separadas por job, com permissões mínimas e auditoria de IAM.
3. **Alertas como código (IaC):** versionar alert policies e notification channels (Terraform), incluindo:
   - erros de execução,
   - falhas de DQ,
   - **silêncio** (quando o pipeline não roda ou não produz dados).
4. **Zero-silêncio (freshness):** detectar automaticamente “não chegou dado” e “não gerou sinal” dentro de janelas.
5. **Config por tabela:** mover parâmetros críticos para BigQuery (com versionamento) e reduzir dependência de redeploy para ajustes.
6. **Reprocessamento seguro:** padronizar reprocessamento (diário → sinais → backtest) com endpoints autenticados e logs auditáveis.

### 2.2 Entregáveis
- Endpoints **privados** (auth obrigatória) para os jobs.
- Terraform em `infra/monitoring/` com:
  - `google_monitoring_notification_channel`
  - `google_monitoring_alert_policy` (log-based + métricas/absence)
- Estrutura `infra/iam/` (ou docs + scripts) para criar e aplicar IAM mínimo por job.
- Tabelas de configuração e leitura real delas nos jobs (fallback para env vars).
- DQ expandido (incluindo intraday uniqueness/freshness).
- Runbook atualizado + “checklist diário do operador”.

---

## 3) Segurança (Cloud Run / Cloud Functions gen2)

### 3.1 Política
- Serviços **privados por padrão** (Require authentication).
- **Scheduler** chama via **OIDC** com Service Account específica do job.
- Nada público (“allow unauthenticated”) exceto endpoints explicitamente necessários — e mesmo assim preferir IAM.

### 3.2 Mudanças obrigatórias
1) Remover `--allow-unauthenticated` dos deploys dos jobs que não precisam ser públicos.  
2) Definir para cada job um par:
   - **Invoker principal**: service account do Scheduler
   - **Runtime identity**: service account do job (separada)
3) Garantir que apenas o invoker tem `roles/run.invoker` para o job/serviço.

### 3.3 Resultado esperado
- Toda execução de job passa a ser rastreável por identidade (SA), com trilha no Audit Log.

---

## 4) IAM: contas e permissões mínimas (least privilege)

### 4.1 Service accounts
Criar uma SA por componente (exemplos):
- `sa-intraday-fetch@...`
- `sa-intraday-candles@...`
- `sa-daily-b3@...`
- `sa-eod-signals@...`
- `sa-backtest@...`
- `sa-dq@...`
- `sa-scheduler-invoker@...` (ou uma por job, se quiser granularidade máxima)

### 4.2 Permissões mínimas por job (padrão)
- BigQuery:
  - `roles/bigquery.dataEditor` (apenas no dataset)
  - `roles/bigquery.jobUser`
- Logging:
  - `roles/logging.logWriter` (se necessário)
- Cloud Run:
  - `roles/run.invoker` para quem chama
  - `roles/iam.serviceAccountUser` apenas quando precisa de `actAs`

---

## 5) Alertas como código (Terraform)

### 5.1 Estrutura
Criar `infra/monitoring/`:
- `main.tf` / `variables.tf` / `outputs.tf`
- módulo para notification channels (email / webhook)
- módulo para políticas:
  - log-based alert policies (erro e DQ FAIL)
  - métricas/absence (silêncio)

### 5.2 Tipos de alerta obrigatórios

#### A) Log-based (evento)
- `job status=ERROR`
- `dq status=FAIL`
- `download COTAHIST failed` (quando exceder tentativas)

#### B) Silêncio (absence / freshness)
Como log-based não faz “contagem/ausência” diretamente, escolher 1 padrão:
1) **Log-based metric** (counter) + alert policy por threshold/absence, ou  
2) “Heartbeat” + `condition_absent`, ou  
3) Job DQ que calcula freshness e escreve log “FAIL_FRESHNESS” (vira log-based alert)

Aplicar o padrão escolhido em todos os componentes críticos:
- diário OHLCV
- sinais EOD
- intraday (raw ou candles)

### 5.3 Anti-spam
- `notification_rate_limit` (ex.: 5–15 min)
- auto-close e agrupamento por job/dia

---

## 6) Zero-silêncio: freshness e completude

### 6.1 Checks obrigatórios (DQ)
Expandir DQ com:
- **Intraday freshness:** `now() - last_point <= X min` (ex.: 45 min)
- **Intraday uniqueness:** duplicatas por `(ticker, timestamp)` abaixo de limiar
- **Diário freshness:** OHLCV do último pregão existe para >= X% dos tickers ativos
- **Sinais freshness:** `sinais_eod` gerado até 22h BRT
- **Backtest freshness:** `backtest_metrics.as_of_date` atualizado

Persistir em `dq_checks_daily` e (opcional) `dq_checks_intraday`.

### 6.2 Ações
- Em `FAIL`: registrar incidente + log estruturado (para alertas)
- Em `WARN`: registrar e notificar (opcional)

---

## 7) Configuração por tabela (reduzir redeploy)

### 7.1 Tabelas
- `parametros_estrategia`:
  - `x_pct`, `target_pct`, `stop_pct`, `horizon_days`, `allow_sell`, `max_signals`
- `pipeline_config` (novo, recomendado):
  - thresholds de DQ (freshness_min, completeness_min)
  - flags de segurança (ex.: `ALLOW_OFFLINE_FALLBACK=false`)

### 7.2 Regras
- Jobs leem config do BigQuery no início.
- Env var é fallback (bootstrap).
- Guardar `config_version` (timestamp/uuid) em cada execução no log e nas tabelas (audit).

---

## 8) Reprocessamento seguro (runbook + ferramenta)

### 8.1 API de reprocessamento (autenticada)
Padronizar parâmetros:
- `date_ref=YYYY-MM-DD`
- `mode=DAILY|EOD|BACKTEST|ALL`
- `force=true|false`

### 8.2 Ferramenta
Criar `tools/reprocess.py`:
- chama endpoints autenticados (ID token)
- valida resultado
- registra `run_id` e links de logs

### 8.3 Garantias
- Reprocesso idempotente (MERGE / replace partition).
- Reprocesso sempre registra “reason=manual_reprocess”.

---

## 9) Critérios de aceite (Definition of Done)

Sprint 5 está pronta quando:
1) Todos os endpoints críticos exigem autenticação e não estão públicos.
2) Existe IaC (Terraform) aplicado e versionado para:
   - notification channels
   - alert policies (erro, DQ FAIL, silêncio)
3) Existe detecção de silêncio com alerta funcionando em 2 cenários simulados:
   - “não entrou diário”
   - “não gerou sinais”
4) Parâmetros principais são lidos de tabela (BigQuery) e uma mudança simples não exige redeploy.
5) Existe procedimento de reprocessamento autenticado e validado, com logs/auditoria.
6) Runbook atualizado, com “checklist diário” e “como responder a cada alerta”.

---

## 10) Fora de escopo (Sprint 5)
- Notícias/sentimento (Reuters etc.)
- Modelos avançados de ML/NN
- Integração com broker / execução automática
- Ajuste por proventos/splits
- Otimização automática de parâmetros

---

## 11) Checklist (PO → equipe)
- Confirmar quais endpoints devem ser 100% privados.
- Definir canais de notificação (email / webhook / Slack).
- Definir thresholds iniciais de silêncio/freshness.
- Confirmar se Terraform será usado (recomendado) ou alternativa (gcloud scripts).

---

## 12) Referências (para docs internas)

```text
Cloud Run — Authentication overview (serviços privados por padrão):
https://cloud.google.com/run/docs/authenticating/overview

Cloud Run — Public (unauthenticated) access (apenas se necessário):
https://cloud.google.com/run/docs/authenticating/public

Cloud Run — Service-to-service authentication (ID token + roles/run.invoker):
https://cloud.google.com/run/docs/authenticating/service-to-service

Cloud Run — IAM roles (inclui execução de jobs e invoker):
https://cloud.google.com/run/docs/reference/iam/roles

Cloud Scheduler — HTTP target auth (OIDC/OAuth):
https://docs.cloud.google.com/scheduler/docs/http-target-auth

Cloud Logging — Log-based alerting policies:
https://docs.cloud.google.com/logging/docs/alerting/log-based-alerts

Cloud Logging — Monitor your logs (log-based metrics, alerting, SQL-based alerts):
https://docs.cloud.google.com/logging/docs/alerting/monitoring-logs

Cloud Monitoring — Create alerting policies with Terraform:
https://docs.cloud.google.com/monitoring/alerts/terraform

Cloud Monitoring — Manage alerting policies with Terraform:
https://docs.cloud.google.com/monitoring/alerts/manage-alerts-terraform

BigQuery — DML / MERGE:
https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax

BigQuery — Clustered tables:
https://cloud.google.com/bigquery/docs/clustered-tables
```
