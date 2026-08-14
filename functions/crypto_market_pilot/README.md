# Crypto market pilot

Piloto de pesquisa, sem ordens e sem capital real, que coleta candles fechados
de um minuto da Binance Spot para `BTCUSDT` e `ETHUSDT` e os grava de forma
idempotente em `crypto_market.candles_1m`.

## Variáveis

- `GCP_PROJECT` (default: `ingestaokraken`)
- `BQ_CRYPTO_DATASET` (default: `crypto_market`)
- `BQ_CRYPTO_CANDLES_1M_TABLE` (default: `candles_1m`)
- `BQ_LOCATION` (default: `us-east1`)
- `CRYPTO_PILOT_PAIRS` (default: `BTCUSDT,ETHUSDT`)
- `CRYPTO_PILOT_LIMIT` (default: `5`)
- `BINANCE_API_BASE_URL` (default: `https://data-api.binance.vision`, endpoint
  público da Binance exclusivo para market data)

## Payload

```json
{
  "pairs": ["BTCUSDT", "ETHUSDT"],
  "limit": 5,
  "dry_run": true
}
```

`start_time` e `end_time` aceitam epoch em milissegundos ou timestamp ISO-8601.
O piloto persiste apenas candles fechados e usa como chave lógica
`exchange + symbol + interval + event_time`.

## Pré-requisitos operacionais

O código não cria o dataset para evitar conceder `bigquery.datasets.create` à
identidade de runtime. Um operador autorizado deve executar uma vez:

```bash
gcloud iam service-accounts create sa-crypto-market-pilot \
  --project=ingestaokraken \
  --display-name='Crypto market pilot'

gcloud projects add-iam-policy-binding ingestaokraken \
  --member='serviceAccount:sa-crypto-market-pilot@ingestaokraken.iam.gserviceaccount.com' \
  --role='roles/bigquery.jobUser'

bq --location=us-east1 mk --dataset ingestaokraken:crypto_market

bq query --location=us-east1 --use_legacy_sql=false \
  'GRANT `roles/bigquery.dataEditor`
   ON SCHEMA `ingestaokraken`.crypto_market
   TO "serviceAccount:sa-crypto-market-pilot@ingestaokraken.iam.gserviceaccount.com"'
```

O comando legado `bq add-iam-policy-binding` pode responder `This feature
requires allowlisting`; use o `GRANT ... ON SCHEMA` acima, que aplica IAM no
dataset por DCL SQL.

Depois do merge em `main`, o workflow `Deploy` publica a função somente se a
service account dedicada existir. A tabela é criada pela função no primeiro
POST real. Depois de todos os deploys concluírem, o mesmo workflow cria ou
atualiza e reativa o Scheduler público `crypto-market-pilot-5m`, sem OIDC. O
payload busca as últimas 120 barras para recuperar automaticamente interrupções
de até aproximadamente duas horas; o `MERGE` idempotente descarta a sobreposição.

Para configurar o job manualmente, se necessário:

```bash
gcloud scheduler jobs create http crypto-market-pilot-5m \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/5 * * * *' \
  --time-zone='Etc/UTC' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/crypto_market_pilot' \
  --http-method=POST \
  --headers='Content-Type=application/json' \
  --message-body='{"pairs":["BTCUSDT","ETHUSDT"],"limit":120,"dry_run":false}' \
  --attempt-deadline=180s
```

Antes de criar o Scheduler manualmente, faça um POST com `dry_run=true`; depois
do primeiro POST real, valide `crypto_market.candles_1m` no BigQuery. Não
configure OIDC enquanto o workflow mantiver `--allow-unauthenticated`. A conta
do workflow precisa de permissão para descrever, criar, atualizar e reativar
jobs do Cloud Scheduler; uma falha nessa etapa deixa o deploy explicitamente
vermelho, em vez de publicar a função sem ativar a coleta recorrente.

## Verificação operacional

A coleta saudável deve ter o job `crypto-market-pilot-5m` ativo em `us-east1`,
linhas recentes para os dois pares e nenhuma duplicidade na chave
`exchange + symbol + interval + event_time`. Se a tabela existir, mas estiver
vazia, confira primeiro os logs da função: uma resposta HTTP 500 indica falha de
persistência e não deve ser interpretada como coleta ativa.
