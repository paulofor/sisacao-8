# Manual de agendamentos no GCP

Este manual descreve os agendamentos necessários para manter o fluxo de ingestão, processamento e alerta do projeto **sisacao-8** operando de forma totalmente automatizada no Google Cloud Platform (GCP). Ele assume que você já implantou as funções disponíveis no repositório (`get_stock_data`, `google_finance_price` e `alerts`) e possui um dataset BigQuery com as tabelas `cotacao_intraday.cotacao_fechamento_diario`, `cotacao_intraday.cotacao_bovespa` e `signals_oscilacoes`.

## 1. Visão geral dos agendamentos

| Agendamento | Serviço GCP | Frequência sugerida | Objetivo | Recursos envolvidos |
|-------------|-------------|---------------------|----------|----------------------|
| Ingestão diária oficial | Cloud Scheduler → Cloud Functions | Todo dia útil às 20:00 (America/Sao_Paulo) | Invocar a função `get_stock_data` para baixar o arquivo oficial da B3 e gravar na tabela de fechamento diário. | Cloud Function `get_stock_data`, tabela `cotacao_intraday.cotacao_fechamento_diario` |
| Complemento intraday opcional | Cloud Scheduler → Cloud Run | A cada 30 minutos entre 10:00 e 18:00 (America/Sao_Paulo) | Acionar o serviço `google_finance_price` para buscar preços recentes no Google Finance. | Serviço HTTP `google_finance_price`, tabela `cotacao_intraday.cotacao_bovespa` |
| Geração de sinais | Scheduled Query BigQuery | Todo dia às 17:40 (America/Sao_Paulo) | Executar `infra/bq/signals_oscilacoes.sql` para popular `cotacao_intraday.signals_oscilacoes`. | BigQuery, tabela `cotacao_intraday.signals_oscilacoes` |
| Notificações | Cloud Scheduler → Cloud Functions | Todo dia às 18:00 (America/Sao_Paulo) | Enviar requisição para a função `alerts` e publicar resumo no Telegram. | Cloud Function `alerts`, tabela `cotacao_intraday.signals_oscilacoes` |

## 2. Pré-requisitos gerais

1. **APIs habilitadas**: ative `cloudfunctions.googleapis.com`, `run.googleapis.com`, `cloudscheduler.googleapis.com`, `bigquery.googleapis.com` e `secretmanager.googleapis.com` no projeto.
2. **Contas de serviço**: crie uma conta dedicada (ex.: `agendamentos-sisacao`) e conceda as funções mínimas:
   - `Cloud Functions Invoker` para chamar `get_stock_data` e `alerts`;
   - `Cloud Run Invoker` para chamar `google_finance_price` se estiver hospedada no Cloud Run;
   - `BigQuery Job User` para executar scheduled queries;
   - `Secret Manager Secret Accessor` caso utilize segredos (`BOT_TOKEN`, `CHAT_ID`).
3. **Autenticação do Cloud Scheduler**: associe a conta de serviço criada em cada job e configure o header `Authorization: Bearer <token>` quando necessário.
4. **Fusos horários**: defina sempre `America/Sao_Paulo` ao criar cron jobs para evitar desvios durante o horário de verão norte-americano.

## 3. Agendamento da função `get_stock_data`

### 3.1 Criação via console

1. Acesse **Cloud Scheduler** no console.
2. Clique em **Create job** e preencha:
   - **Name**: `get-stock-data-diario`;
   - **Frequency**: `0 20 * * 1-5` (dias úteis às 20:00);
   - **Time zone**: `America/Sao_Paulo`;
   - **Target type**: `HTTP`.
3. Em **URL**, informe o endpoint da função (ex.: `https://us-central1-ingestaokraken.cloudfunctions.net/get_stock_data`).
4. Em **HTTP method**, selecione `POST`.
5. Em **Body**, não é necessário enviar conteúdo. Os tickers monitorados são
   lidos do arquivo `functions/get_stock_data/tickers.txt` no repositório.
6. Em **Authentication**, selecione **Add OAuth token** e escolha a conta de serviço com permissão `Cloud Functions Invoker`.
7. Salve o job e teste executando manualmente uma vez para validar logs e escrita no BigQuery.

### 3.2 Criação via CLI

Se preferir usar o Cloud SDK:

```bash
gcloud scheduler jobs create http get-stock-data-diario \
    --schedule="0 20 * * 1-5" \
    --time-zone="America/Sao_Paulo" \
    --uri="https://us-central1-ingestaokraken.cloudfunctions.net/get_stock_data" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --oidc-service-account-email=agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com \
    --oidc-token-audience="https://us-central1-ingestaokraken.cloudfunctions.net/get_stock_data"
```

Os exemplos acima já utilizam o projeto `ingestaokraken` na região `us-central1`. Ajuste apenas se precisar implantar em outro ambiente. O parâmetro `--oidc-token-audience` garante que a função reconheça o token emitido pelo Cloud Scheduler.

## 4. Agendamento do serviço `google_finance_price`

1. Implante a função como serviço HTTP no Cloud Run (outra opção é mantê-la como Cloud Function HTTP).
2. Crie um job no Cloud Scheduler com frequência `0,30 10-18 * * 1-5` para rodar de segunda a sexta a cada 30 minutos.
3. Configure o método `POST` e o payload esperado (ex.: `{ "limit": 50 }`).
4. Caso utilize Cloud Run, selecione **Add OIDC token** e aponte para o serviço (`--oidc-token-audience=https://google_finance_price-<hash>-<region>-a.run.app`).
5. Verifique nos logs do Cloud Run se há retorno `200 OK` e registros novos na tabela `cotacao_bovespa`.

## 5. Scheduled Query do BigQuery

1. No console do BigQuery, navegue até **Scheduled queries** e clique em **Create scheduled query**.
2. Defina:
   - **Name**: `signals_oscilacoes`;
   - **Schedule**: `Daily` às `17:40` em `America/Sao_Paulo`;
   - **Destination**: `ingestaokraken.cotacao_intraday.signals_oscilacoes`, opção **Write if empty** ou **Overwrite** na partição do dia.
3. Cole o conteúdo de [`infra/bq/signals_oscilacoes.sql`](../infra/bq/signals_oscilacoes.sql) no editor de SQL.
4. Em **Service account**, selecione a conta `agendamentos-sisacao` com função `BigQuery Job User`.
5. Salve e execute uma vez para criar a tabela inicial. Monitore o histórico em **Scheduled Queries > Job History** para validar futuras execuções.

## 6. Agendamento da função `alerts`

1. Garanta que os segredos `BOT_TOKEN` e `CHAT_ID` estejam disponíveis no Secret Manager e vinculados à função `alerts`.
2. Crie um job no Cloud Scheduler com cron `0 18 * * 1-5` para enviar o resumo após o horário de pregão.
3. Configure o endpoint `https://us-central1-ingestaokraken.cloudfunctions.net/alerts` com método `POST` e corpo `{ "only_summary": true }` (ou conforme os parâmetros aceitos pela função).
4. Associe a conta de serviço com permissão `Cloud Functions Invoker` e teste disparando manualmente.

## 7. Monitoramento e operação contínua

- **Logs**: utilize o Cloud Logging para acompanhar o sucesso ou falha dos jobs. Configure filtros salvos por função.
- **Alertas operacionais**: crie alertas no Cloud Monitoring monitorando a métrica "Job execution status" do Cloud Scheduler e "BigQuery scheduled query failures".
- **Rotinas de auditoria**: revise trimestralmente a conta de serviço e as permissões concedidas aos jobs.
- **Fallback manual**: documente um procedimento manual para executar as funções (`gcloud functions call` ou `curl`) caso o Scheduler fique indisponível.

## 8. Checklist rápido

1. [ ] APIs necessárias habilitadas.
2. [ ] Conta de serviço `agendamentos-sisacao` criada com permissões mínimas.
3. [ ] Job `get-stock-data-diario` criado e testado.
4. [ ] Job intraday do `google_finance_price` ativo (se aplicável).
5. [ ] Scheduled Query `signals_oscilacoes` criada e validada.
6. [ ] Job `alerts` configurado com segredos disponíveis.
7. [ ] Alertas operacionais ativados no Cloud Monitoring.

Seguindo estes passos você garante que todas as automações do projeto são executadas de forma confiável no GCP, reduzindo o trabalho manual e mantendo a base de dados e alertas sempre atualizados.
