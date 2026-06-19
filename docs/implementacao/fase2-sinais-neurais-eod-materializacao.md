# Materialização do dataset de treino neural EOD

Esta implementação adiciona a Cloud Function HTTP `functions/neural_training_dataset`, responsável por materializar o dataset supervisionado da Fase 2 neural em `cotacao_intraday.neural_eod_training_dataset`.

## Fluxo operacional

1. Ler candles históricos de `cotacao_intraday.cotacao_ohlcv_diario` dentro da janela solicitada.
2. Ler feriados de `cotacao_intraday.feriados_b3` quando a tabela estiver disponível.
3. Executar `sisacao8.neural_dataset.build_training_dataset` com parâmetros versionados de label e split temporal.
4. Adicionar `created_at`, `dataset_snapshot` e `metadata_json` de auditoria.
5. Remover linhas existentes do mesmo `dataset_snapshot` quando `replace_snapshot=true`.
6. Gravar o resultado em `cotacao_intraday.neural_eod_training_dataset` via BigQuery append.

## Endpoint

Entrada HTTP JSON ou query string:

```json
{
  "start_date": "2021-01-01",
  "end_date": "2026-06-18",
  "dataset_snapshot": "neural_eod_training_dataset_2026-06-18_v1",
  "replace_snapshot": true,
  "min_history_days": 20,
  "horizon_days": 15,
  "embargo_days": 15
}
```

Resposta esperada:

```json
{
  "status": "ok",
  "dataset_snapshot": "neural_eod_training_dataset_2026-06-18_v1",
  "start_date": "2021-01-01",
  "end_date": "2026-06-18",
  "rows": 12345,
  "splits": {"train": 8000, "validation": 2000, "test": 2000, "embargo": 345}
}
```

## Variáveis de ambiente

| Variável | Default | Uso |
| --- | --- | --- |
| `BQ_INTRADAY_DATASET` | `cotacao_intraday` | Dataset BigQuery das tabelas de candles e treino neural. |
| `BQ_DAILY_TABLE` | `cotacao_ohlcv_diario` | Tabela fonte dos candles diários. |
| `BQ_HOLIDAYS_TABLE` | `feriados_b3` | Tabela de feriados B3. |
| `BQ_NEURAL_TRAINING_DATASET_TABLE` | `neural_eod_training_dataset` | Tabela destino do dataset supervisionado. |
| `BQ_LOCATION` | `us-east1` | Localidade dos jobs BigQuery. |
| `NEURAL_TRAINING_LOOKBACK_DAYS` | `1825` | Janela default quando `start_date` não é informado. |
| `NEURAL_TRAINING_MIN_HISTORY_DAYS` | `20` | Histórico mínimo por ticker para gerar features. |

## Publicação GCP

Com `gcloud` autenticado no projeto `ingestaokraken`, publicar a partir da raiz do repositório:

```bash
gcloud functions deploy neural_training_dataset \
  --gen2 \
  --runtime python312 \
  --region us-east1 \
  --source functions/neural_training_dataset \
  --entry-point neural_training_dataset \
  --trigger-http \
  --set-env-vars BQ_INTRADAY_DATASET=cotacao_intraday,BQ_DAILY_TABLE=cotacao_ohlcv_diario,BQ_HOLIDAYS_TABLE=feriados_b3,BQ_NEURAL_TRAINING_DATASET_TABLE=neural_eod_training_dataset,BQ_LOCATION=us-east1
```

A service account usada no deploy precisa de permissão de leitura em `cotacao_ohlcv_diario`/`feriados_b3` e escrita em `neural_eod_training_dataset`.
