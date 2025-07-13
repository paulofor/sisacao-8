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
