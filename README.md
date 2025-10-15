# sisacao-8

Coleta cotações de ações e carrega no **BigQuery** usando **Google Cloud Functions**.

## Como usar

1. Instale as dependências de desenvolvimento:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Crie um arquivo `.env` baseado em `config/env.example`. O arquivo inclui o
   IP estático `AWS_STATIC_IP`, útil para liberar o acesso em integrações que
   exigem *allowlist* de origem.

3. Garanta que os tickers desejados estejam marcados como ativos na tabela
   `cotacao_intraday.acao_bovespa`, utilizada pela função
   `google_finance_price`. A função `get_stock_data` reutiliza essa mesma
   lista ao buscar os fechamentos diários. Se preferir testar com um arquivo
   local, edite `functions/get_stock_data/tickers.txt` (um símbolo por linha)
   e defina a variável de ambiente `TICKERS_FILE` apontando para ele.

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

### Troubleshooting do deploy Lightsail

O repositório também possui um workflow opcional chamado
`Deploy backend to Lightsail`. Se o passo `appleboy/scp-action` falhar com as
mensagens `ssh: no key found` ou `dial tcp ...:22: i/o timeout`, siga o guia em
[docs/troubleshooting_scp_action.md](docs/troubleshooting_scp_action.md) para
configurar a chave SSH e liberar o acesso ao servidor corretamente. Já se o
log mostrar `sudo password required: configure passwordless sudo for deploy or
set LIGHTSAIL_SUDO_PASSWORD secret` — acompanhado de erros ao executar
`systemctl` — é necessário concluir a configuração descrita em
[docs/lightsail-deploy.md](docs/lightsail-deploy.md) para que o usuário
`deploy` tenha permissão de `sudo` (sem senha ou fornecendo a senha via
`LIGHTSAIL_SUDO_PASSWORD`).

### IP estático para integrações externas

Quando for necessário liberar o tráfego de saída para integrações hospedadas
na AWS, utilize o IP estático `34.194.252.70`. Esse endereço deve ser adicionado
às listas de permissões (*allowlists*) de serviços externos que exigem
configuração explícita de IP.

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
