# Fase 1 — Especificação e schema dos sinais EOD neurais

## Objetivo executado

Esta fase cria o contrato mínimo para iniciar o sistema de sinais EOD baseado em redes neurais sem alterar a geração operacional atual de `sinais_eod`. A rede neural passa a ter uma tabela própria para publicar probabilidades auditáveis, e a conversão dessas probabilidades em sinais finais permanece responsabilidade de uma camada posterior do `eod_signals`.

## Artefato criado

- Script BigQuery: `infra/bq/16_neural_eod_predictions.sql`.

O script define a tabela `cotacao_intraday.neural_eod_predictions` e a view `cotacao_intraday.vw_neural_eod_predictions_latest`, que retorna a predição mais recente por `reference_date`, `valid_for`, `ticker` e `model_id`.

## Tabela de predições neurais

A tabela `neural_eod_predictions` armazena somente saídas brutas e metadados de inferência. Ela não substitui `sinais_eod` e não deve ser consumida pelo backtest diário diretamente.

Campos obrigatórios principais:

| Campo | Tipo | Regra |
|---|---|---|
| `reference_date` | DATE | Pregão de fechamento usado como base da inferência. |
| `valid_for` | DATE | Próximo pregão em que a predição pode ser transformada em sinal. |
| `ticker` | STRING | Ticker B3 normalizado no mesmo padrão de `cotacao_ohlcv_diario`. |
| `model_id` | STRING | Família estável do modelo neural. |
| `model_version` | STRING | Versão treinada/promovida do artefato. |
| `feature_version` | STRING | Versão do contrato de features usado na inferência. |
| `inference_config_version` | STRING | Versão dos thresholds e parâmetros de inferência. |
| `prob_up` | FLOAT64 | Probabilidade estimada para cenário direcional de alta. |
| `prob_down` | FLOAT64 | Probabilidade estimada para cenário direcional de queda. |
| `prob_neutral` | FLOAT64 | Probabilidade estimada para cenário neutro. |
| `suggested_action` | STRING | `BUY`, `SELL` ou `HOLD`, antes dos filtros operacionais. |
| `confidence` | FLOAT64 | Maior probabilidade direcional usada na sugestão. |
| `decision_threshold` | FLOAT64 | Threshold aplicado para transformar probabilidade em sugestão. |
| `feature_snapshot` | STRING | Hash ou identificador reproduzível das features calculadas. |
| `source_snapshot` | STRING | Hash ou identificador reproduzível dos dados de origem. |
| `job_run_id` | STRING | Identificador único da execução de inferência. |
| `created_at` | TIMESTAMP | Momento da gravação da predição. |

Campos opcionais como `label_version`, `close`, `financial_volume` e `metadata_json` permitem rastrear contexto de treino, inspeção operacional e extensões sem mudar imediatamente o contrato canônico.

## Schema mínimo de features

A primeira versão de features deve ser tabular, simples e auditável. O contrato inicial recomendado é `feature_eod_tabular_v1`.

| Grupo | Features mínimas |
|---|---|
| Retornos | `return_5d`, `return_10d`, `return_20d`. |
| Volatilidade | `volatility_10d`, `volatility_20d`. |
| Candle diário | `daily_range_pct`, `intraday_return_pct`, `gap_open_pct`. |
| Volume | `financial_volume`, `financial_volume_z20`, `volume_ratio_20d`. |
| Tendência/distância | `distance_high_20d_pct`, `distance_low_20d_pct`, `distance_sma_20d_pct`. |
| Qualidade | `has_missing_ohlcv`, `has_zero_volume`, `is_suspicious_candle`. |

Regras obrigatórias do contrato de features:

1. todas as features de `(ticker, reference_date)` devem usar apenas dados conhecidos até o fechamento de `reference_date`;
2. normalizadores e imputadores devem ser ajustados somente no conjunto de treino e reaplicados sem refit na validação, teste e inferência;
3. `feature_snapshot` deve mudar quando qualquer dado de entrada, janela, normalização ou lista de features mudar;
4. features ausentes devem ser explicitamente imputadas ou marcadas por flags de qualidade, nunca ignoradas silenciosamente.

## Convenções de versionamento

### `model_id`

Identifica a família estável do modelo, sem incluir retreinos pontuais.

Padrão recomendado:

```text
neural_eod_<familia>
```

Exemplos:

- `neural_eod_mlp`;
- `neural_eod_residual_mlp`;
- `neural_eod_cnn1d`.

### `model_version`

Identifica o artefato promovido para inferência ou teste controlado.

Padrão recomendado:

```text
<model_id>_v<major>_<YYYYMMDD>
```

Exemplo: `neural_eod_mlp_v1_20260618`.

Mudanças de arquitetura, labels, universo, janelas ou hiperparâmetros relevantes devem gerar nova versão.

### `feature_version`

Identifica o contrato de features e não o valor calculado para um dia específico.

Padrão recomendado:

```text
feature_eod_tabular_v<major>
```

Exemplo: `feature_eod_tabular_v1`.

### `inference_config_version`

Identifica thresholds e parâmetros de decisão usados para preencher `suggested_action`.

Padrão recomendado:

```text
neural_eod_inference_config_v<major>
```

Exemplo: `neural_eod_inference_config_v1`.

## Contrato de entrada da inferência

O futuro job `functions/neural_eod_predictions/` deverá receber:

| Parâmetro | Obrigatório | Descrição |
|---|---:|---|
| `date_ref` | Não | Pregão base; se omitido, usar o último pregão fechado válido. |
| `model_id` | Não | Família do modelo; default configurado para o modelo aprovado. |
| `model_version` | Não | Versão do artefato; default configurado para a versão aprovada. |
| `dry_run` | Não | Quando verdadeiro, calcula sem gravar no BigQuery. |
| `job_run_id` | Não | Identificador externo; se omitido, gerar UUID. |

Pré-condições:

- `date_ref` deve ser dia de pregão já encerrado;
- deve existir histórico mínimo suficiente para calcular `feature_version`;
- o modelo solicitado deve estar aprovado para inferência experimental ou paper trading;
- a execução não pode usar dados posteriores a `date_ref`.

## Contrato de saída da inferência

Para cada ticker elegível, o job deve gravar uma linha em `neural_eod_predictions` com probabilidades normalizadas e uma sugestão preliminar:

- `BUY` se `prob_up >= min_prob_up` e `prob_up > prob_down`;
- `SELL` se `prob_down >= min_prob_down` e `prob_down > prob_up`;
- `HOLD` nos demais casos.

A soma `prob_up + prob_down + prob_neutral` deve ser aproximadamente `1.0`, respeitando tolerância numérica documentada no job. A tabela aceita múltiplas execuções para o mesmo ticker e data; consumidores operacionais devem usar `vw_neural_eod_predictions_latest` ou filtrar por `job_run_id` específico.

## Contrato para a camada de decisão EOD

O futuro modo `SIGNAL_SOURCE=neural` do `eod_signals` deve consumir a tabela de predições e aplicar regras operacionais adicionais antes de gravar `sinais_eod`:

1. ler somente predições do `reference_date` desejado e de versões aprovadas;
2. descartar `HOLD`;
3. reaplicar confiança mínima, liquidez mínima e limite máximo de sinais;
4. calcular `entry`, `target`, `stop` e `horizon_days` usando a regra canônica do projeto;
5. gravar `model_version`, `ranking_key`, `source_snapshot`, `job_run_id` e `config_version` para rastreabilidade;
6. nunca apagar ou sobrescrever sinais heurísticos sem decisão explícita de promoção.

## Critérios de saída atendidos

- DDL da tabela `neural_eod_predictions` criado.
- View operacional para última predição criada.
- Schema mínimo de features definido.
- Convenções de `model_id`, `model_version`, `feature_version` e `inference_config_version` documentadas.
- Contratos de entrada e saída da inferência documentados.
- Contrato de consumo pelo futuro modo neural do `eod_signals` documentado.

## Próximos passos

1. Aplicar `infra/bq/16_neural_eod_predictions.sql` no BigQuery.
2. Implementar o dataset histórico supervisionado da Fase 2.
3. Criar validações automatizadas para probabilidades, versões e ausência de vazamento temporal.
4. Implementar o job `functions/neural_eod_predictions/` somente após o dataset e o modelo baseline estarem definidos.
