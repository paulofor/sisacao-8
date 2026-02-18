# Configurações essenciais do Cloud Scheduler

Este documento consolida as configurações necessárias para que todos os jobs do projeto **sisacao-8** sejam executados pelo [Cloud Scheduler](https://cloud.google.com/scheduler) com segurança e previsibilidade. Utilize-o como checklist na criação ou revisão de ambientes.

> ℹ️ Consulte também o [manual completo de agendamentos](./manual_agendamentos_gcp.md) para passos detalhados de implantação.

## Pré-requisitos gerais

| Item | Descrição |
|------|-----------|
| APIs habilitadas | `cloudscheduler.googleapis.com`, `cloudfunctions.googleapis.com`, `run.googleapis.com`, `bigquery.googleapis.com`, `secretmanager.googleapis.com`. |
| Conta de serviço | `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` com as permissões: `Cloud Scheduler Admin`, `Cloud Functions Invoker`, `Cloud Run Invoker` (se aplicável), `BigQuery Job User`, `Secret Manager Secret Accessor`. |
| Fuso horário padrão | `America/Sao_Paulo`. Ajuste apenas se o ambiente exigir outra região operacional. |
| Monitoramento | Alertas no Cloud Monitoring para falhas de execução e dashboards no Cloud Logging por job. |

## Resumo dos jobs

### 1. `get-stock-data-diario`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Function `get_stock_data` |
| Endpoint | `https://us-central1-<projeto>.cloudfunctions.net/get_stock_data` |
| Método HTTP | `POST` (body vazio) |
| Cron | `0 20 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` |
| Cabeçalhos adicionais | `Content-Type: application/json` |
| Logs esperados | Inserções na tabela `cotacao_intraday.cotacao_ohlcv_diario` |
| Observações | Execute manualmente após a criação para validar permissões e escrita no BigQuery. |

### 2. `google-finance-price-intraday`

> Consulte o guia [Validação do agendamento `google_finance_price` (Cloud Run)](./google_finance_price_cloud_run.md) para o passo a passo completo de confirmação do endpoint, ajuste do Scheduler e testes no Cloud Logging/BigQuery.

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Run (ou Function HTTP) `google_finance_price` |
| Endpoint | `https://google-finance-price-<hash>-<region>-a.run.app` (ajuste conforme o deploy) |
| Método HTTP | `POST` |
| Payload | `{ "limit": 50 }` (ajuste conforme parâmetros aceitos) |
| Cron | `0,30 10-18 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` e `--oidc-token-audience` apontando para o endpoint do serviço |
| Logs esperados | Registros novos na tabela `cotacao_intraday.cotacao_b3` |
| Observações | Utilize Cloud Run Invoker para autenticar e monitore latência para evitar sobrecarga. |

### 3. `intraday-candles`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Function `intraday_candles` |
| Endpoint | `https://us-central1-<projeto>.cloudfunctions.net/intraday_candles` |
| Método HTTP | `POST` (body vazio ou `{ "date": "YYYY-MM-DD" }`) |
| Cron | `10 18 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` |
| Logs esperados | Inserções nas tabelas `candles_intraday_15m` e `candles_intraday_1h` |
| Observações | Reprocessamentos idempotentes podem ser feitos enviando o parâmetro `date`. |

### 4. `eod-signals`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Function `eod_signals` |
| Endpoint | `https://us-central1-<projeto>.cloudfunctions.net/eod_signals` |
| Método HTTP | `POST` |
| Payload | `{ "date": "YYYY-MM-DD" }` (opcional) |
| Cron | `0 19 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` |
| Logs esperados | Inserções na tabela `cotacao_intraday.sinais_eod` |
| Observações | Execute após a função `intraday_candles` para garantir dados completos. |

### 5. `alerts-diario`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Function `alerts` |
| Endpoint | `https://us-central1-<projeto>.cloudfunctions.net/alerts` |
| Método HTTP | `POST` |
| Payload | `{ "only_summary": true }` |
| Cron | `0 18 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` |
| Segredos necessários | `BOT_TOKEN`, `CHAT_ID` configurados no Secret Manager e montados na função |
| Observações | Monitore o canal de destino (ex.: Telegram) para validar o recebimento das mensagens. |

## Checklist de validação

1. [ ] Todos os jobs aparecem como **Enabled** no Cloud Scheduler.
2. [ ] Última execução de cada job finalizou como **Success** e possui log no Cloud Logging.
3. [ ] Funções `intraday_candles` e `eod_signals` rodaram nas últimas 24 horas sem falhas.
4. [ ] Alertas operacionais configurados (e-mail ou webhook) para falhas de jobs.
5. [ ] Revisão trimestral das permissões da conta de serviço concluída.

Mantendo este documento atualizado você garante que as rotinas automáticas do projeto continuem executando sem intervenção manual.
