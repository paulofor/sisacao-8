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

3. Ajuste a lista de tickers em `functions/get_stock_data/tickers.txt`.

4. Teste localmente a Cloud Function `get_stock_data`:

   ```bash
   pip install functions-framework
   functions-framework --target=get_stock_data
   ```

Consulte os comentários nos diretórios para mais detalhes.

## Deploy

O workflow `.github/workflows/deploy.yml` realiza o deploy automático da função
para o **Google Cloud Functions** sempre que houver push ou pull request para a
branch `master`. Também é possível acioná-lo manualmente via *workflow_dispatch*.
Configure o segredo `GCP_SA_KEY` (além do `BQ_TABLE` usado pela função) no
repositório do GitHub. A função será publicada no projeto `ingestaokraken`,
região `us-central1`.

O comando executado é:

```bash
gcloud functions deploy get_stock_data \
    --runtime python311 \
    --trigger-http \
    --entry-point get_stock_data \
    --source functions/get_stock_data \
    --allow-unauthenticated \
    --project ingestaokraken \
    --region us-central1
```

## Monitoramento

Passos para agendar a consulta diária e montar um painel no Looker Studio
estão descritos em [docs/monitoramento.md](docs/monitoramento.md).
