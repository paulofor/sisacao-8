# sisacao-8

Estrutura inicial para coletar cotações de ações e carregar no **BigQuery** usando **Google Cloud Functions**.

## Como usar

1. Instale as dependências de desenvolvimento:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Crie um arquivo `.env` baseado em `config/env.example`.

3. Quando as funções estiverem implementadas, você poderá testá‑las localmente:

   ```bash
   pip install functions-framework
   functions-framework --target=<function_name>
   ```

Consulte os comentários nos diretórios para mais detalhes.
