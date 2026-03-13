# Validação do agendamento `google_finance_price` (Cloud Run)

Este guia documenta como confirmar se o serviço `google_finance_price` está publicado no **Cloud Run**, ajustar o job `Intraday` do **Cloud Scheduler** para apontar para o endpoint correto com autenticação OIDC e validar a ingestão na tabela `cotacao_intraday.cotacao_b3`.

> 🛈 Caso você opte por expor `google_finance_price` como **Cloud Function HTTP**, os comandos são equivalentes, alterando apenas as flags de invocação (principalmente o papel `Cloud Functions Invoker` e o endpoint `cloudfunctions.net`).

## Configuração recomendada do Scheduler (do zero)

Use o bloco abaixo para criar/atualizar o job com uma configuração segura para Cloud Run autenticado:

```bash
PROJECT_ID="ingestaokraken"
REGION="us-east1"
JOB_NAME="Intraday"
SERVICE_NAME="google-finance-price"
SCHEDULER_SA="agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com"
CRON="*/5 9-18 * * 1-5"   # exemplo: a cada 5 min em horário comercial (UTC)
TIME_ZONE="America/Sao_Paulo"
BODY='{"limit":50}'

SERVICE_URL="$(gcloud run services describe ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --format='value(status.url)')"

# 1) Permissão para o Scheduler invocar o Cloud Run
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role="roles/run.invoker"

# 2) Cria (ou atualiza) o job HTTP com OIDC
if gcloud scheduler jobs describe ${JOB_NAME} --project=${PROJECT_ID} --location=${REGION} >/dev/null 2>&1; then
  gcloud scheduler jobs update http ${JOB_NAME} \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --schedule="${CRON}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${SERVICE_URL}" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body="${BODY}" \
    --oidc-service-account-email="${SCHEDULER_SA}" \
    --oidc-token-audience="${SERVICE_URL}"
else
  gcloud scheduler jobs create http ${JOB_NAME} \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --schedule="${CRON}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${SERVICE_URL}" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body="${BODY}" \
    --oidc-service-account-email="${SCHEDULER_SA}" \
    --oidc-token-audience="${SERVICE_URL}"
fi

# 3) Teste manual imediato
gcloud scheduler jobs run ${JOB_NAME} --project=${PROJECT_ID} --location=${REGION}
```

> Dica: se aparecer 403, quase sempre é `roles/run.invoker` ausente ou `--oidc-token-audience` divergente da URL do serviço.

## 1. Confirmar se o serviço está implantado e anotar a URL

1. Liste o serviço no Cloud Run e recupere a URL pública:

   ```bash
   gcloud run services describe google-finance-price \
     --project=ingestaokraken \
     --region=us-east1 \
     --format="value(status.url)"
   ```

2. Guarde a URL completa retornada (exemplo: `https://google-finance-price-abcdefg-uc.a.run.app`). Ela será usada como alvo do job e como `--oidc-token-audience`.

## 2. Atualizar o job `Intraday` do Cloud Scheduler

1. Verifique a configuração atual do job:

   ```bash
   gcloud scheduler jobs describe Intraday \
     --location=us-east1 \
     --project=ingestaokraken
   ```

2. Aplique o endpoint correto do Cloud Run e habilite OIDC com a conta de serviço do Scheduler (exemplo `agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com`):

   ```bash
   SERVICE_URL="https://google-finance-price-abcdefg-uc.a.run.app"  # substitua pela URL real

   gcloud scheduler jobs update http Intraday \
     --location=us-east1 \
     --project=ingestaokraken \
     --uri="${SERVICE_URL}" \
     --http-method=POST \
     --headers="Content-Type=application/json" \
     --body='{"limit":50}' \
     --oidc-service-account-email="agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com" \
     --oidc-token-audience="${SERVICE_URL}"
   ```

3. Caso o serviço esteja em Cloud Function, substitua `--uri` e `--oidc-token-audience` pelo endpoint `https://us-east1-ingestaokraken.cloudfunctions.net/google_finance_price` e garanta o papel **Cloud Functions Invoker**.

## 3. Garantir permissões de invocação

A conta de serviço do Scheduler precisa do papel correto para autenticar via OIDC:

```bash
gcloud run services add-iam-policy-binding google-finance-price \
  --member="serviceAccount:agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-east1 \
  --project=ingestaokraken
```

Para Cloud Functions, use `roles/cloudfunctions.invoker` e o comando `gcloud functions add-iam-policy-binding`.

## 4. Testar a execução e verificar logs

1. Dispare uma execução manual pelo Scheduler (CLI ou console):

   ```bash
   gcloud scheduler jobs run Intraday \
     --location=us-east1 \
     --project=ingestaokraken
   ```

2. No **Cloud Logging**, filtre pelos recursos **Cloud Run Revision** (ou **Cloud Function**) e pelo rótulo `service=google-finance-price` para confirmar o retorno `200`.

3. Valide a ingestão na tabela `cotacao_intraday.cotacao_b3` conferindo os logs de escrita ou consultando o BigQuery:

   ```bash
   bq query --project_id=ingestaokraken """
   SELECT COUNT(*) AS registros_hoje
   FROM `ingestaokraken.cotacao_intraday.cotacao_b3`
   WHERE DATE(inserted_at) = CURRENT_DATE('America/Sao_Paulo');
   """
   ```

4. Caso a execução falhe, revise o `--oidc-token-audience` (deve ser idêntico à URL do serviço) e confirme que o papel de **Invoker** foi aplicado.

## 5. Diagnóstico rápido para erro HTTP 403

Quando aparecer `POST 403 https://google-finance-price-...run.app/` nos logs do container, o problema costuma ser de **autorização na invocação**, não de código Python.

Checklist direto:

1. **Cloud Run exige autenticação?**
   - Se sim, o chamador (Cloud Scheduler, backend ou curl) precisa enviar token OIDC válido.
2. **Conta de serviço do Scheduler/backend tem `roles/run.invoker`?**
   - Sem esse papel, o Cloud Run devolve 403 imediatamente.
3. **`--oidc-token-audience` é exatamente a URL do serviço?**
   - Qualquer diferença (barra final, domínio errado, endpoint antigo) pode gerar 403.
4. **Job aponta para o endpoint correto (produção atual)?**
   - URL de revisão antiga ou serviço diferente também quebra autenticação.
5. **Erro 403 durante gravação no BigQuery (stacktrace em `google.cloud.bigquery`)?**
   - Nesse caso é IAM do BigQuery: conceda ao runtime service account papéis como `roles/bigquery.dataEditor` (dataset) e `roles/bigquery.jobUser` (projeto), conforme política da sua organização.

Com esse passo a passo você separa rapidamente dois cenários que parecem iguais no console:
- **403 na entrada HTTP do Cloud Run** → permissões de invocação/OIDC.
- **403 dentro do stacktrace do BigQuery** → permissões de acesso aos dados/jobs no BigQuery.

Seguindo este checklist você garante que o job `Intraday` está apontando para o endpoint correto, autenticando via OIDC e gravando os preços intradiários no BigQuery.
