# Fase 2 — Dataset de treino dos sinais EOD neurais

## Objetivo executado

Esta fase implementa o contrato inicial para montar um dataset histórico supervisionado por `(ticker, reference_date)`, separando claramente features conhecidas até o fechamento do pregão `D` das labels calculadas com candles futuros apenas para treino histórico.

## Artefatos criados

- Código reutilizável: `sisacao8/neural_dataset.py`.
- Testes unitários: `tests/test_neural_dataset.py`.
- Script BigQuery: `infra/bq/17_neural_eod_training_dataset.sql`.

## Features da versão `feature_eod_tabular_v1`

O builder calcula retornos de 5, 10 e 20 pregões, volatilidades de 10 e 20 pregões, range diário, retorno intradiário, gap de abertura, volume financeiro, z-score de volume financeiro em 20 pregões, razão de volume em 20 pregões, distâncias para máxima/mínima/média de 20 pregões e flags de qualidade.

Todas as janelas são calculadas por ticker usando somente dados até `reference_date`; não há uso de `D+1` em features.

## Labels da versão `label_eod_barrier_v1`

As labels seguem a regra operacional por barreiras:

1. `entry_buy = close(D) * (1 - entry_pct)`;
2. `entry_sell = close(D) * (1 + entry_pct)`;
3. a partir de `valid_for = D+1`, verifica-se em até `horizon_days` se a entrada foi tocada;
4. se a entrada foi tocada, avalia-se se target ou stop ocorreu primeiro de forma conservadora;
5. a linha vira `up` se o cenário BUY superar SELL e o retorno mínimo líquido; vira `down` no caso simétrico; caso contrário vira `neutral`.

## Split temporal

A função `assign_temporal_splits` cria partições `train`, `validation` e `test` em ordem cronológica, mantendo todos os tickers de uma mesma data na mesma partição e removendo datas de embargo entre treino/validação e validação/teste. O embargo padrão acompanha o horizonte de labels para reduzir vazamento por janelas futuras sobrepostas.

## Contrato BigQuery

A tabela `cotacao_intraday.neural_eod_training_dataset` registra o dataset materializado com versões de feature/label, split temporal, features, labels auxiliares e metadados de snapshot. A view `vw_neural_eod_training_dataset_quality` resume distribuição de classes, janela histórica, quantidade de tickers e flags de qualidade por versão/split.

## Critérios de saída atendidos

- Dataset histórico por ticker/data definido e implementado.
- Labels `up`, `down` e `neutral` criadas por regra versionada de barreiras.
- Separação treino/validação/teste cronológica com embargo temporal.
- Prevenção de vazamento temporal documentada e refletida nos helpers.
