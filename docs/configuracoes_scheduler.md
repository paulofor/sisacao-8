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
| Logs esperados | Inserções na tabela `cotacao_intraday.cotacao_fechamento_diario` |
| Observações | Execute manualmente após a criação para validar permissões e escrita no BigQuery. |

### 2. `google-finance-price-intraday`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Cloud Run (ou Function HTTP) `google_finance_price` |
| Endpoint | `https://google-finance-price-<hash>-<region>-a.run.app` (ajuste conforme o deploy) |
| Método HTTP | `POST` |
| Payload | `{ "limit": 50 }` (ajuste conforme parâmetros aceitos) |
| Cron | `0,30 10-18 * * 1-5` |
| Time zone | `America/Sao_Paulo` |
| Autenticação | OIDC token com a conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` e `--oidc-token-audience` apontando para o endpoint do serviço |
| Logs esperados | Registros novos na tabela `cotacao_intraday.cotacao_bovespa` |
| Observações | Utilize Cloud Run Invoker para autenticar e monitore latência para evitar sobrecarga. |

### 3. `signals-oscilacoes`

| Campo | Valor recomendado |
|-------|-------------------|
| Serviço-alvo | Scheduled Query do BigQuery |
| Dataset/Tabela | `ingestaokraken.cotacao_intraday.signals_oscilacoes` |
| Script SQL | [`infra/bq/signals_oscilacoes.sql`](../infra/bq/signals_oscilacoes.sql) |
| Cron | `40 17 * * *` (Daily às 17:40) |
| Time zone | `America/Sao_Paulo` |
| Autenticação | Conta `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` com permissão `BigQuery Job User` |
| Estratégia de gravação | `WRITE_TRUNCATE` na partição do dia ou `WRITE_APPEND`, conforme política operacional |
| Observações | Habilite notificações por e-mail para falhas na scheduled query. |

### 4. `alerts-diario`

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
3. [ ] Scheduled Query do BigQuery executou nas últimas 24 horas sem erros.
4. [ ] Alertas operacionais configurados (e-mail ou webhook) para falhas de jobs.
5. [ ] Revisão trimestral das permissões da conta de serviço concluída.

Mantendo este documento atualizado você garante que as rotinas automáticas do projeto continuem executando sem intervenção manual.
