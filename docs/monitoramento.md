# Monitoramento

Este guia descreve como automatizar a geração de sinais e como visualizar os resultados.

## Scheduled Query diária

1. Abra o console do BigQuery e navegue até **Scheduled queries**.
2. Clique em **Create scheduled query**.
3. Defina:
   - **Nome**: `signals_oscilacoes`
   - **Frequência**: `Daily`.
   - **Hora de execução**: `17:40` no fuso `America/Sao_Paulo`.
4. Em **Destination**, escolha `project.dataset` e marque **Write if empty**.
5. Cole o conteúdo de [`infra/bq/signals_oscilacoes.sql`](../infra/bq/signals_oscilacoes.sql) no campo de SQL.
6. Salve para que a consulta rode automaticamente e substitua apenas a partição do dia.

## Dashboard no Looker Studio

1. Acesse [Looker Studio](https://lookerstudio.google.com/) e crie um novo relatório.
2. Selecione **BigQuery** como fonte de dados e a tabela `project.dataset.signals_oscilacoes`.
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
       --set-env-vars=BQ_SIGNALS_TABLE=project.dataset.signals_oscilacoes
   ```

2. Teste enviando uma requisição:

   ```bash
   curl -X POST "https://REGION-PROJECT.cloudfunctions.net/alerts"
   ```

A função consulta os sinais do dia corrente, registra a contagem por ticker e envia um resumo para o Telegram caso as variáveis `BOT_TOKEN` e `CHAT_ID` estejam configuradas.
