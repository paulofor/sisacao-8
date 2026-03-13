# Validação do agendamento `google_finance_price` (Cloud Run)

Este guia documenta como confirmar se o serviço `google_finance_price` está publicado no **Cloud Run**, ajustar o job `Intraday` do **Cloud Scheduler** para apontar para o endpoint correto com autenticação OIDC e validar a ingestão na tabela `cotacao_intraday.cotacao_b3`.

> 🛈 Caso você opte por expor `google_finance_price` como **Cloud Function HTTP**, os comandos são equivalentes, alterando apenas as flags de invocação (principalmente o papel `Cloud Functions Invoker` e o endpoint `cloudfunctions.net`).

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

Seguindo este checklist você garante que o job `Intraday` está apontando para o endpoint correto, autenticando via OIDC e gravando os preços intradiários no BigQuery.
