# Ops API — contrato dos endpoints `/ops/*`

A Ops API exposta pelo backend Spring Boot consolida as views `vw_ops_*` do
BigQuery em payloads prontos para o frontend (React/MUI). Os endpoints são
read-only e seguem o padrão JSON descrito abaixo.

- **Base URL (dev):** `http://localhost:8080`
- **Base URL (prod):** `/api`

> Todos os payloads são serializados em UTC (`OffsetDateTime`) e utilizam o
> formato `YYYY-MM-DD` para datas simples.

## 1. `GET /ops/overview`

Retorna o "semáforo" diário com os principais indicadores do pipeline:

```json
{
  "asOf": "2026-02-20T21:55:00Z",
  "lastTradingDay": "2026-02-20",
  "nextTradingDay": "2026-02-23",
  "pipelineHealth": "OK",
  "dqHealth": "PASS",
  "signalsReady": true,
  "signalsCount": 5,
  "lastSignalsGeneratedAt": "2026-02-20T21:58:10Z"
}
```

## 2. `GET /ops/pipeline`

Lista um registro por job/component, combinando o último run-id, deadlines e
monitoramento de silêncio:

```json
[
  {
    "jobName": "daily_ohlcv",
    "lastRunAt": "2026-02-20T21:40:00Z",
    "lastStatus": "OK",
    "minutesSinceLastRun": 12,
    "deadlineAt": "2026-02-20T22:00:00Z",
    "silent": false,
    "lastRunId": "run_20260220_214000_daily_ohlcv"
  }
]
```

## 3. `GET /ops/dq/latest`

Últimos data-quality checks sincronizados via `vw_ops_dq_latest`:

```json
[
  {
    "checkDate": "2026-02-20",
    "checkName": "intraday_freshness",
    "status": "PASS",
    "details": "{...}",
    "createdAt": "2026-02-20T21:45:10Z"
  }
]
```

## 4. `GET /ops/incidents/open`

Incidentes ainda abertos (status `OPEN` ou `INVESTIGATING`):

```json
[
  {
    "incidentId": "inc_20260220_001",
    "checkName": "intraday_uniqueness",
    "checkDate": "2026-02-20",
    "severity": "HIGH",
    "source": "DQ",
    "summary": "dq FAIL: intraday_uniqueness acima do limiar",
    "status": "OPEN",
    "runId": "run_20260220_214500_dq_checks",
    "createdAt": "2026-02-20T21:46:00Z"
  }
]
```

## 5. `GET /ops/signals/next`

Top 5 sinais para o próximo pregão determinado pelas views operacionais:

```json
[
  {
    "validFor": "2026-02-23",
    "ticker": "PETR4",
    "side": "BUY",
    "entry": 43.0,
    "target": 46.01,
    "stop": 39.99,
    "score": 0.78,
    "rank": 1,
    "createdAt": "2026-02-20T21:58:10Z"
  }
]
```

## 6. `GET /ops/signals/history`

Histórico parametrizado de sinais EOD.

### Parâmetros

| Nome  | Tipo    | Obrigatório | Exemplo       | Observações                                    |
|-------|---------|-------------|---------------|------------------------------------------------|
| from  | string  | Sim         | `2026-02-01`  | Data mínima no formato `YYYY-MM-DD`.           |
| to    | string  | Sim         | `2026-02-20`  | Precisa ser >= `from`.                         |
| limit | integer | Não         | `100`         | Máximo controlado por `historyMaxRows` (200).  |

### Exemplo de resposta

```json
[
  {
    "dateRef": "2026-02-20",
    "validFor": "2026-02-23",
    "ticker": "PETR4",
    "side": "BUY",
    "entry": 43.0,
    "target": 46.01,
    "stop": 39.99,
    "score": 0.78,
    "rank": 1,
    "createdAt": "2026-02-20T21:58:10Z"
  }
]
```

## 7. Tratamento de erros

| Cenário                           | Código | Corpo                                               |
|----------------------------------|--------|-----------------------------------------------------|
| Datas inválidas (`from`/`to`)    | 400    | `{ "message": "O parâmetro 'from' não pode ser..." }` |
| BigQuery indisponível/falha SQL  | 502    | `{ "message": "Falha ao consultar BigQuery" }`        |
| Erro inesperado interno          | 500    | `{ "message": "Erro inesperado ao consultar a Ops API." }` |

Os erros seguem o mesmo formato (`timestamp`, `status`, `error`, `message` e
`path`), graças ao `OpsExceptionHandler`.

## 8. Dependências

- Configuração: `sisacao.ops.bigquery.*` em `application.properties`
- Views BigQuery versionadas em `infra/bq/views_ops.sql`
- Cliente: `BigQueryOpsClient` → executa queries parametrizadas por view

Qualquer alteração em nomes de views ou dataset deve ser refletida nas
properties da aplicação.
