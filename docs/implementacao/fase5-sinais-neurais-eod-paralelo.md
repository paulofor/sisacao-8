# Fase 5 — Sinais neurais em paralelo

## Status

Executada em 2026-06-19.

## Objetivo

Permitir que o `eod_signals` consuma `cotacao_intraday.neural_eod_predictions` e grave sinais neurais versionados em `sinais_eod`, sem substituir imediatamente o fluxo heurístico atual.

## Alterações implementadas

- Adicionado o parâmetro `SIGNAL_SOURCE=heuristic|neural|hybrid` no job `functions/eod_signals`.
- Mantido `heuristic` como valor padrão para preservar o comportamento atual.
- Criado consumo controlado de `neural_eod_predictions` por `reference_date` e `valid_for`.
- Adicionado filtro de ações `HOLD`, confiança mínima de BUY/SELL e limite máximo de sinais por dia.
- Reutilizada a regra canônica de entrada, alvo, stop e horizonte:
  - BUY: entrada abaixo do fechamento;
  - SELL: entrada acima do fechamento.
- Gravados sinais neurais com `model_version` própria no formato `neural:<model_version>` e `ranking_key=neural_confidence_v1`.
- Ajustada a limpeza pré-inserção para remover apenas sinais da mesma `date_ref` e `model_version`, evitando apagar sinais heurísticos já gravados no mesmo pregão.
- Adicionado modo `hybrid`, que combina confiança neural com score heurístico/backtest para ranqueamento controlado.

## Parâmetros operacionais

| Parâmetro | Default | Descrição |
|---|---:|---|
| `SIGNAL_SOURCE` | `heuristic` | Fonte de geração: `heuristic`, `neural` ou `hybrid`. |
| `BQ_NEURAL_PREDICTIONS_TABLE` | `neural_eod_predictions` | Tabela de predições neurais. |
| `NEURAL_MIN_BUY_CONFIDENCE` | `0.60` | Confiança mínima para BUY. |
| `NEURAL_MIN_SELL_CONFIDENCE` | `0.60` | Confiança mínima para SELL. |
| `NEURAL_SIGNAL_RANKING_KEY` | `neural_confidence_v1` | Chave de ranking dos sinais neurais. |
| `HYBRID_SIGNAL_RANKING_KEY` | `hybrid_neural_heuristic_v1` | Chave de ranking dos sinais híbridos. |

## Contrato de execução em paralelo

1. O modo padrão permanece heurístico.
2. Para gerar sinais neurais, executar `eod_signals` com `SIGNAL_SOURCE=neural` ou payload `signal_source=neural`.
3. O job busca predições neurais para o mesmo `reference_date` e `valid_for` calculado pelo calendário B3.
4. Apenas predições `BUY`/`SELL` acima dos thresholds viram sinais.
5. A persistência apaga somente sinais da mesma versão neural antes de reinserir, preservando o paralelo com sinais heurísticos.
6. O `backtest_daily` continua validando a tabela `sinais_eod` sem alteração de contrato.

## Critérios de saída

- O `eod_signals` aceita `SIGNAL_SOURCE=neural` sem alterar o default produtivo.
- Sinais neurais são rastreáveis por `model_version`, `ranking_key`, `source_snapshot`, `job_run_id` e `config_version`.
- O fluxo paralelo não remove sinais heurísticos já existentes para a mesma data.
- Há testes unitários cobrindo consulta das predições e geração de sinais neurais a partir de confiança.
