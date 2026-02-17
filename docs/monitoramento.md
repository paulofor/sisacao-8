# Monitoramento

Este guia descreve como automatizar a geração de sinais e como visualizar os resultados.

## Função diária de sinais

1. Implante `functions/eod_signals` e configure o Cloud Scheduler conforme o [manual](manual_agendamentos_gcp.md).
2. Verifique no Cloud Logging se a execução registrou a mensagem "stored" com o número de sinais enviados ao BigQuery.
3. Acompanhe a tabela `ingestaokraken.cotacao_intraday.signals_eod_v0` para confirmar a inserção.
4. Em caso de reprocessamento, invoque a função com `{ "date": "YYYY-MM-DD" }`.

## Dashboard no Looker Studio

1. Acesse [Looker Studio](https://lookerstudio.google.com/) e crie um novo relatório.
2. Selecione **BigQuery** como fonte de dados e a tabela `ingestaokraken.cotacao_intraday.signals_eod_v0`.
3. Autorize o acesso e carregue os campos.
4. Monte visualizações filtrando por `dt` e `ticker`.
5. Salve o relatório para acompanhar os sinais diariamente.

## (Opcional) Função de alertas

1. Implante a Cloud Function de HTTP em `functions/alerts`:

   ```bash
   gcloud functions deploy alerts \
       --runtime=python311 \
       --trigger-http \
       --allow-unauthenticated \
       --set-secrets=BOT_TOKEN=bot-token:latest,CHAT_ID=chat-id:latest \
       --set-env-vars=BQ_SIGNALS_TABLE=ingestaokraken.cotacao_intraday.signals_eod_v0
   ```

2. Teste enviando uma requisição:

   ```bash
   curl -X POST "https://us-central1-ingestaokraken.cloudfunctions.net/alerts"
   ```

A função consulta os sinais do dia corrente na tabela `signals_eod_v0`, registra a contagem por ticker e envia um resumo para o Telegram quando `BOT_TOKEN` e `CHAT_ID` estão configurados.
