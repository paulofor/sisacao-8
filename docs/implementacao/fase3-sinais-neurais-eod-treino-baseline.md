# Fase 3 — Treino neural baseline para sinais EOD

Esta fase cria o primeiro contrato executável para treinar um modelo neural EOD simples, auditável e versionado. O objetivo é produzir um baseline MLP tabular comparável às estratégias existentes, sem promover automaticamente sinais operacionais.

## Entregáveis

- Código reutilizável: `sisacao8/neural_training.py`.
- Job produtivo HTTP: `functions/neural_training`.
- Testes unitários: `tests/test_neural_training.py` e `tests/test_neural_training_function.py`.
- Registro BigQuery: `infra/bq/18_neural_model_registry.sql`.

## Modelo baseline

O baseline usa uma MLP pequena com entrada tabular, camadas densas, dropout leve e saída `softmax` para as classes estáveis:

1. `down`;
2. `neutral`;
3. `up`.

A versão inicial é:

- `model_id`: `neural_eod_mlp`;
- `model_version`: `neural_eod_mlp_v1_20260618`;
- `feature_version`: `feature_eod_tabular_v1`;
- `label_version`: `label_eod_barrier_v1`.

## Features usadas

O treino consome as features criadas na Fase 2, incluindo preços OHLCV, retornos de 5/10/20 dias, volatilidades, gap, volume financeiro padronizado, razão de volume e distâncias para máxima, mínima e média de 20 dias.

O scaler é ajustado somente no split `train` e persistido no manifesto para evitar vazamento de validação/teste.

## Métricas registradas

A avaliação registra, por split cronológico:

- quantidade de linhas;
- matriz de confusão 3x3;
- precisão, recall, F1 e suporte por classe;
- acurácia global;
- precisão direcional para predições `up`/`down`;
- cobertura direcional, isto é, fração de linhas em que o modelo não escolhe `neutral`.

## Artefato versionado

`train_baseline_mlp()` grava os seguintes arquivos em `<artifact_dir>/<model_version>/`:

- `model.keras`: artefato Keras versionado;
- `manifest.json`: metadados de versão, contrato de features/labels, hiperparâmetros, hash do dataset, janela histórica, métricas e scaler.

O hash `dataset_snapshot` é calculado a partir de ticker, data de referência, split e label das linhas materializadas, permitindo rastrear o conjunto usado no treino.


## Execução produtiva

A Cloud Function HTTP `neural_training` fecha a lacuna entre os dados de treino e a tela de acompanhamento de treinos. Ela:

1. lê o snapshot solicitado, ou o snapshot mais recente, em `cotacao_intraday.neural_eod_training_dataset`;
2. filtra linhas com `dataset_split` preenchido para treinar apenas splits cronológicos válidos;
3. executa `train_baseline_mlp()` com hiperparâmetros recebidos por payload ou defaults auditáveis;
4. publica `model.keras` e `manifest.json` em `gs://<NEURAL_MODEL_ARTIFACT_BUCKET>/<NEURAL_MODEL_ARTIFACT_PREFIX>/<model_version>` quando o bucket estiver configurado;
5. insere uma linha em `cotacao_intraday.neural_model_registry` com status inicial `candidate`, URI do artefato, contrato de features/labels e métricas de validação/teste.

Payload mínimo recomendado:

```json
{
  "dataset_snapshot": "neural_eod_training_dataset_2026-06-18_v1",
  "model_version": "neural_eod_mlp_v1_20260620",
  "epochs": 40,
  "batch_size": 256,
  "status": "candidate"
}
```

Após a inserção no registry, o endpoint `GET /ops/neural/training-runs` passa a retornar o treino para a tela **Redes neurais — Treinos**.

## Registro em BigQuery

O script `18_neural_model_registry.sql` cria `cotacao_intraday.neural_model_registry`, que deve receber uma linha por artefato treinado com status inicial `candidate`. A promoção para `shadow`, `paper` ou `approved` permanece manual/controlada em fases posteriores.

## Critérios de saída

A Fase 3 está concluída quando:

1. o código consegue preparar arrays sem vazamento entre splits;
2. a MLP baseline pode ser treinada e salva com versão;
3. o job produtivo publica o artefato e grava o registry com status `candidate`;
4. as métricas mínimas por classe, matriz de confusão, precisão direcional e cobertura são calculadas;
5. existe tabela de registro para governança dos artefatos;
6. nenhum sinal operacional é gerado automaticamente.
