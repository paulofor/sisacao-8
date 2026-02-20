# sisacao-8 — Especificação da Sprint 6 (Revisada)  
## Backend “Ops API” + Views no BigQuery para consumo do **seu Frontend (React/MUI)**

**Projeto:** sisacao-8 (B3)  
**Sprint:** 6 (revisada para o stack atual)  
**Objetivo macro:** disponibilizar no **backend Spring Boot** endpoints read-only que entreguem, em formato pronto para UI, todas as informações necessárias para o seu frontend acompanhar:

- **Saúde do pipeline** (OK/ERROR + “silêncio”)
- **DQ checks** (PASS/WARN/FAIL)
- **Incidentes** (abertos/últimos)
- **Sinais do próximo pregão** (top 5)

> Nesta sprint **não** criamos outro frontend nem Looker Studio.  
> O foco é: **BigQuery (views) → Spring Boot (Ops API) → seu Frontend (React)**.

---

## 1) Contexto (baseline)

Você já tem no repo:

- Frontend: `frontend/app` (React + Vite + TS + MUI + TanStack Query)
- Backend: `backend/sisacao-backend` (Spring Boot), com BigQuery clients e endpoints:
  - `GET /data-collections/messages`
  - `GET /data-collections/intraday-summary`
  - `GET /data-collections/intraday-daily-counts`
  - `GET /data-collections/intraday-latest-records`

A Sprint 6 cria um “módulo de operação” semelhante, porém focado em:
**pipeline status / dq / incidentes / sinais**.

---

## 2) Entregáveis

### 2.1 BigQuery (SQL versionado)
- `infra/bq/views_ops.sql` (ou pasta `infra/bq/views/ops/*.sql`) com as views:
  - `vw_ops_overview`
  - `vw_ops_pipeline_status`
  - `vw_ops_dq_latest`
  - `vw_ops_signals_next_session`
  - `vw_ops_signals_history`
  - `vw_ops_incidents_open`

> Observação: o dataset onde essas views ficam deve ser configurável por ambiente (dev/prod).

### 2.2 Backend (Spring Boot)
Novos pacotes (sugestão):
- `com.sisacao.backend.ops` (controller/service/dto)
- `com.sisacao.backend.ops.bigquery` (client/queries/properties)

Novos endpoints (todos GET / read-only):
- `GET /ops/overview`
- `GET /ops/pipeline`
- `GET /ops/dq/latest`
- `GET /ops/incidents/open`
- `GET /ops/signals/next`
- `GET /ops/signals/history?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=...`

### 2.3 Documentação
- `backend/README.md` (atualizar com os endpoints /ops)
- `frontend/app/README.md` (notas de integração e baseURL)
- `docs/ops_api.md` (contrato dos endpoints, exemplos de payload)

---

## 3) Contratos dos endpoints (payloads)

### 3.1 `GET /ops/overview`
Retorna 1 objeto:
```json
{
  "asOf": "2026-02-20T21:55:00-03:00",
  "lastTradingDay": "2026-02-20",
  "nextTradingDay": "2026-02-23",
  "pipelineHealth": "OK",
  "dqHealth": "PASS",
  "signalsReady": true,
  "signalsCount": 5,
  "lastSignalsGeneratedAt": "2026-02-20T21:58:10-03:00"
}
```

### 3.2 `GET /ops/pipeline`
Lista por job/componente:
```json
[
  {
    "jobName": "daily_ohlcv",
    "lastRunAt": "2026-02-20T21:40:00-03:00",
    "lastStatus": "OK",
    "minutesSinceLastRun": 12,
    "deadlineAt": "2026-02-20T22:00:00-03:00",
    "isSilent": false,
    "lastRunId": "run_20260220_214000_daily_ohlcv"
  }
]
```

### 3.3 `GET /ops/dq/latest`
Últimos checks:
```json
[
  {
    "checkDate": "2026-02-20",
    "checkName": "intraday_freshness",
    "status": "PASS",
    "details": "{...}",
    "createdAt": "2026-02-20T21:45:10-03:00"
  }
]
```

### 3.4 `GET /ops/incidents/open`
Incidentes abertos:
```json
[
  {
    "incidentId": "inc_20260220_001",
    "createdAt": "2026-02-20T21:46:00-03:00",
    "severity": "HIGH",
    "source": "DQ",
    "summary": "dq FAIL: intraday_uniqueness acima do limiar",
    "status": "OPEN",
    "runId": "run_20260220_214500_dq_checks"
  }
]
```

### 3.5 `GET /ops/signals/next`
Top 5 sinais do próximo pregão:
```json
[
  {
    "validFor": "2026-02-23",
    "ticker": "PETR4",
    "side": "BUY",
    "entry": 43.00,
    "target": 46.01,
    "stop": 39.99,
    "score": 0.78,
    "rank": 1,
    "createdAt": "2026-02-20T21:58:10-03:00"
  }
]
```

### 3.6 `GET /ops/signals/history`
- Parâmetros:
  - `from` e `to` (obrigatórios)
  - `limit` (opcional, default 200)

---

## 4) BigQuery (Views) — guia de implementação

### 4.1 Princípios
- Views devem:
  - retornar **poucas colunas e poucas linhas** (pronto para UI)
  - usar filtros por data e LIMIT no histórico
  - centralizar regras (silêncio, health geral, próximo pregão)

### 4.2 Sugestões de cálculo (exemplos)
- “silêncio”: `minutes_since_last_run > threshold` (threshold vindo de `pipeline_config`)
- `pipeline_health`:
  - `FAIL` se houver algum job crítico em `ERROR` ou `is_silent=true`
  - `WARN` se houver `WARN`
  - `OK` caso contrário
- `signals_ready`:
  - true se existir `sinais_eod` para `valid_for = nextTradingDay`

---

## 5) Backend (Spring Boot) — guia de implementação

### 5.1 Configuração por properties (novo)
Criar:
- `OpsBigQueryProperties` com `@ConfigurationProperties(prefix="sisacao.ops.bigquery")`
Campos sugeridos:
- `enabled` (bool)
- `projectId`
- `dataset` (default “monitoring” ou outro)
- nomes das views (default `vw_ops_*`)
- `historyMaxRows` (default 200)

> Manter no padrão que vocês já usam em `DataCollectionBigQueryProperties`.

### 5.2 BigQuery client (novo)
Criar `BigQueryOpsClient` que:
- monta queries simples `SELECT * FROM <view>`
- usa parâmetros nomeados quando houver data/limit (`@from`, `@to`, `@limit`)
- faz parsing de campos com “fallback seguro” (strings/números/datas)

### 5.3 Service (novo)
Criar `OpsService` que agrega:
- overview (combina pipeline + dq + sinais)
- pipeline status
- dq latest
- incidents open
- signals next + history

### 5.4 Controller (novo)
Criar `OpsController` com `@RequestMapping("/ops")`.

### 5.5 CORS (recomendado para dev)
Como o frontend em dev roda em outra porta, adicionar CORS controlado por config (ex.: permitir `http://localhost:5173` em profile `dev`).

---

## 6) Plano de trabalho (tarefas)

### 6.1 Data / BigQuery
- [ ] Criar/ajustar views `vw_ops_*` (SQL versionado)
- [ ] Validar com dados reais (dia útil + cenário de falha)
- [ ] Garantir que todas as views funcionam mesmo quando “não há dados” (retornar vazio/valores default)

### 6.2 Backend
- [ ] Criar `OpsBigQueryProperties`
- [ ] Criar DTOs (`OpsOverview`, `PipelineJobStatus`, `DqCheck`, `OpsIncident`, `Signal`)
- [ ] Criar `BigQueryOpsClient`
- [ ] Criar `OpsService`
- [ ] Criar `OpsController`
- [ ] Implementar paginação simples no histórico (limit)
- [ ] (Opcional) cache curto em memória no backend (30–120s) para endpoints pesados

### 6.3 QA / Testes
- [ ] `@WebMvcTest(OpsController)` com `MockBean OpsService` (contrato JSON)
- [ ] Teste de “from/to inválidos” → 400 com mensagem clara
- [ ] Teste de “BigQuery indisponível” → 502/500 com erro amigável

### 6.4 Documentação
- [ ] `docs/ops_api.md` com exemplos de resposta
- [ ] Atualizar READMEs com os novos endpoints

---

## 7) Critérios de aceite (Definition of Done)

Sprint 6 está pronta quando:
1) As views `vw_ops_*` existem e estão versionadas no repo.
2) O backend expõe `/ops/*` e retorna JSON conforme contratos.
3) Dá para testar localmente:
   - backend `:8080` respondendo
   - chamadas HTTP funcionando (curl/Postman)
4) Os endpoints funcionam em:
   - dia normal (dados presentes)
   - cenário de falha/silêncio (sem quebrar)
5) Documentação atualizada.

---

## 8) Fora de escopo (Sprint 6)
- Melhorias de estratégia de sinal (ML, notícias, etc.)
- Execução automática de ordens
- Autenticação/SSO completa do frontend (pode virar sprint separada)

---

## 9) Referências (implementação)
```text
Spring Boot — Externalized Configuration / @ConfigurationProperties:
https://docs.spring.io/spring-boot/reference/features/external-config.html

BigQuery — Parameterized queries (Java):
https://docs.cloud.google.com/bigquery/docs/parameterized-queries

BigQuery Java — QueryJobConfiguration.Builder (named parameters):
https://docs.cloud.google.com/java/docs/reference/google-cloud-bigquery/latest/com.google.cloud.bigquery.QueryJobConfiguration.Builder
```
