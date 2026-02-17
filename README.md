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
   `google_finance_price`. Os preços coletados por essa função são inseridos
   na tabela intraday `ingestaokraken.cotacao_intraday.cotacao_b3`. A
   função `get_stock_data` reutiliza essa mesma lista ao buscar os fechamentos
   diários. Se preferir testar com um arquivo local, edite
   `functions/get_stock_data/tickers.txt` (um símbolo por linha) e defina a
   variável de ambiente `TICKERS_FILE` apontando para ele.

4. Crie e mantenha a tabela de feriados da B3 com `infra/bq/feriados_b3.sql`.
   As funções `google_finance_price` e `get_stock_data` consultam
   `ingestaokraken.cotacao_intraday.feriados_b3` e pulam a coleta quando a
   data corrente estiver marcada como feriado ativo.

   O script já inclui os calendários de 2026 e 2027; no início de cada ano,
   atualize com os próximos feriados oficiais da B3 para manter a automação.

5. A função `get_stock_data` já grava candles diários em formato OHLCV (`open`,
   `high`, `low`, `close`, `volume`). Para idempotência em reprocessamentos,
   configure `BQ_DAILY_LOAD_STRATEGY` com `DELETE_PARTITION_APPEND` (padrão)
   ou `MERGE` (staging + chave lógica `ticker`+`reference_date`).

6. Teste localmente a Cloud Function `get_stock_data`:

   ```bash
   pip install functions-framework
   functions-framework --target=get_stock_data
   ```

7. Gere os candles intraday consolidados executando a Cloud Function
   `intraday_candles`. Ela lê os registros crus da tabela
   `cotacao_intraday.cotacao_b3`, agrega em janelas de 15 minutos e grava os
   candles normalizados nas tabelas `candles_intraday_15m` e `candles_intraday_1h`.
   O job aceita o parâmetro opcional `date=YYYY-MM-DD` via query string para
   reprocessamentos idempotentes.

8. Após o fechamento, acione a função `eod_signals` (até 22h BRT) para gerar os
   sinais condicionais do dia. O resultado é salvo na tabela
   `cotacao_intraday.signals_eod_v0` e contém `entry`, `target`, `stop`,
   `rank`, `model_version`, `source_snapshot` e `code_version` para auditoria.

Consulte os comentários nos diretórios para mais detalhes.

## Deploy

O workflow `.github/workflows/deploy.yml` realiza o deploy automático da função
para o **Google Cloud Functions** sempre que houver push ou pull request para a
branch `master`. Também é possível acioná-lo manualmente via *workflow_dispatch*.
Configure o segredo `GCP_SA_KEY` (além do `BQ_TABLE` usado pela função) no
repositório do GitHub. A função será publicada no projeto `ingestaokraken`,
região `us-central1`.

### Troubleshooting do deploy Lightsail

O repositório também possui workflows opcionais para publicar backend e
frontend na mesma VPS. Se o passo `appleboy/scp-action` falhar com as mensagens
`ssh: no key found` ou `dial tcp ...:22: i/o timeout`, siga o guia em
[docs/troubleshooting_scp_action.md](docs/troubleshooting_scp_action.md) para
configurar a chave SSH e liberar o acesso ao servidor corretamente. Já se o log
mostrar `sudo password required: configure passwordless sudo for deploy or set
LIGHTSAIL_SUDO_PASSWORD secret` — acompanhado de erros ao executar `systemctl`
— é necessário concluir a configuração descrita em
[docs/lightsail-deploy.md](docs/lightsail-deploy.md) para que o usuário
`deploy` tenha permissão de `sudo` (sem senha ou fornecendo a senha via
`LIGHTSAIL_SUDO_PASSWORD`).

#### Publicação automática do backend

O workflow `Deploy backend to Lightsail` compila o artefato Java com Maven e o
envia para `/opt/sisacao/app/sisacao-backend.jar`, reiniciando o serviço
`sisacao-backend.service` em seguida.

#### Publicação automática do frontend

O workflow `Deploy frontend to Lightsail` reutiliza a mesma estrutura: instala
as dependências do Vite/React, gera a build de produção (`npm run build`) e
publica o conteúdo estático em `/opt/sisacao/app/frontend`. Antes de mover a
nova versão para o diretório definitivo, o job cria um backup temporário em
`/opt/sisacao/tmp`, garantindo que o conteúdo antigo possa ser descartado com
segurança.

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
