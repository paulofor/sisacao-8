# sisacao-8

Coleta cotações de ações e carrega no **BigQuery** usando **Google Cloud Functions**.

## Como usar

1. Instale as dependências de desenvolvimento:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Crie um arquivo `.env` baseado em `config/env.example`.

3. Teste localmente a Cloud Function `get_stock_data`:

   ```bash
   pip install functions-framework
   functions-framework --target=get_stock_data
   ```

Consulte os comentários nos diretórios para mais detalhes.

## Deploy

O workflow `.github/workflows/deploy.yml` realiza o deploy automático da função
para o **Google Cloud Functions** a cada push na branch `main`. Configure os
segredos `GCP_SA_KEY` e `GCP_PROJECT` (além do `BQ_TABLE` usado pela função) no
repositório do GitHub.

O comando executado é:

```bash
gcloud functions deploy get_stock_data \
    --runtime python311 \
    --trigger-http \
    --entry-point get_stock_data \
    --source functions/get_stock_data \
    --allow-unauthenticated
```
