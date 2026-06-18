# Fase 3 — Treino neural baseline para sinais EOD

Esta fase cria o primeiro contrato executável para treinar um modelo neural EOD simples, auditável e versionado. O objetivo é produzir um baseline MLP tabular comparável às estratégias existentes, sem promover automaticamente sinais operacionais.

## Entregáveis

- Código reutilizável: `sisacao8/neural_training.py`.
- Testes unitários: `tests/test_neural_training.py`.
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

## Registro em BigQuery

O script `18_neural_model_registry.sql` cria `cotacao_intraday.neural_model_registry`, que deve receber uma linha por artefato treinado com status inicial `candidate`. A promoção para `shadow`, `paper` ou `approved` permanece manual/controlada em fases posteriores.

## Critérios de saída

A Fase 3 está concluída quando:

1. o código consegue preparar arrays sem vazamento entre splits;
2. a MLP baseline pode ser treinada e salva com versão;
3. as métricas mínimas por classe, matriz de confusão, precisão direcional e cobertura são calculadas;
4. existe tabela de registro para governança dos artefatos;
5. nenhum sinal operacional é gerado automaticamente.
