# Fase 4 — Inferência EOD neural em shadow mode

Esta fase cria o primeiro job executável de inferência neural EOD sem impacto operacional em `sinais_eod`. O objetivo é gerar probabilidades auditáveis diariamente, validar estabilidade por alguns pregões e manter a decisão operacional bloqueada até as fases seguintes.

## Artefatos criados

- Código reutilizável: `sisacao8/neural_inference.py`.
- Cloud Function/job: `functions/neural_eod_predictions/`.
- Testes unitários: `tests/test_neural_inference.py`.
- Tabela de destino: `cotacao_intraday.neural_eod_predictions`, criada na Fase 1 por `infra/bq/16_neural_eod_predictions.sql`.

## Contrato do job

Entrada HTTP opcional:

| Campo | Uso |
|---|---|
| `date_ref` ou `date` | Data de referência do pregão fechado. Se omitida, usa o dia atual após 18h BRT ou o dia anterior antes do cutoff. |
| `force` | Permite execução antes do cutoff apenas para reprocessamento controlado. |
| `job_run_id` | Identificador externo opcional da execução. |
| `artifact_uri` | Caminho local ou `gs://` para artefato contendo `manifest.json` e `model.keras`; se omitido, o job consulta o registry. |
| `model_version` | Versão específica a buscar no registry. |

Variáveis principais:

| Variável | Padrão | Descrição |
|---|---|---|
| `BQ_INTRADAY_DATASET` | `cotacao_intraday` | Dataset BigQuery operacional. |
| `BQ_DAILY_TABLE` | `cotacao_ohlcv_diario` | Candles diários usados para montar features. |
| `BQ_NEURAL_EOD_PREDICTIONS_TABLE` | `neural_eod_predictions` | Tabela de predições brutas. |
| `BQ_NEURAL_MODEL_REGISTRY_TABLE` | `neural_model_registry` | Registry de modelos treinados. |
| `NEURAL_MODEL_ID` | `neural_eod_mlp` | Família de modelo usada na consulta ao registry. |
| `NEURAL_MODEL_STATUSES` | `shadow,approved` | Status permitidos para inferência sem produção. |
| `NEURAL_DECISION_THRESHOLD` | `0.60` | Threshold direcional para `BUY`/`SELL`; abaixo disso vira `HOLD`. |
| `NEURAL_INFERENCE_LOOKBACK_DAYS` | `90` | Janela de candles carregada para calcular features. |

## Fluxo implementado

1. valida cutoff de 18h BRT, exceto quando `force=true`;
2. resolve `reference_date` e `valid_for` pelo próximo pregão útil, usando feriados quando disponíveis;
3. seleciona um artefato local/GCS explícito ou o modelo mais recente com status `shadow`/`approved` no registry;
4. carrega `manifest.json`, `model.keras` e o scaler do treinamento;
5. monta features EOD com o mesmo contrato tabular da Fase 2, sem labels e sem candles futuros;
6. gera probabilidades `down`, `neutral`, `up`;
7. converte probabilidades em `suggested_action` (`BUY`, `SELL`, `HOLD`) somente para auditoria;
8. grava em `neural_eod_predictions` com `feature_snapshot`, `source_snapshot`, `job_run_id` e metadados de qualidade.

## Garantias de shadow mode

- O job não importa nem chama `eod_signals`.
- O job não grava em `sinais_eod`.
- `suggested_action` é apenas uma decisão preliminar auditável; sinais operacionais continuam bloqueados até a Fase 5.
- O consumo por `backtest_daily` continua indireto e inexistente nesta fase.

## Critérios de saída

- Predições são persistidas na tabela de shadow mode para cada ticker elegível do pregão fechado.
- Todas as linhas têm versão de modelo, versão de features, configuração de inferência e snapshots.
- A soma das probabilidades por linha é normalizada para `1.0`.
- Testes unitários cobrem classificação `BUY`/`SELL`/`HOLD` e montagem das linhas auditáveis.
