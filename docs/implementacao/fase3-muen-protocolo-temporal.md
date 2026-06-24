# Fase 3 MUEN — Protocolo temporal

**Data:** 2026-06-24  
**Documento normativo:** `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`  
**Status:** implementada em código e schema base

## Objetivo

Implementar o protocolo temporal da Fase 3 do MUEN v1 para impedir que pesquisa,
HPO, leaderboard ou geradores de candidatos consultem o período final de
holdout. A pesquisa passa a ser estruturada como nested expanding walk-forward,
com treino expansivo, calibração exclusiva, embargo e teste externo por fold.

## Configuração inicial implementada

A configuração padrão segue a sugestão normativa do MUEN:

```yaml
min_train_sessions: 504
outer_folds: 5
outer_test_sessions: 63
calibration_sessions: 42
embargo_sessions: 15
locked_holdout_sessions: 126
split_mode: expanding_walk_forward
```

## Implementação

- `NestedWalkForwardConfig`: contrato versionável de quantidade de sessões por
  janela temporal.
- `WalkForwardFold`: janela auditável de um fold externo, contendo treino,
  calibração e teste externo.
- `NestedWalkForwardPlan`: plano completo com folds e início/fim do locked
  holdout.
- `build_nested_walk_forward_plan`: gera folds externos com treino expansivo,
  calibração exclusiva e embargo antes do teste externo.
- `assign_research_holdout_split`: marca o dataset persistido apenas como
  `research` ou `locked_holdout`, evitando materializar papéis de folds
  sobrepostos como se fossem splits mutuamente exclusivos.
- `neural_training_dataset`: aceita `split_mode=nested_expanding_walk_forward`
  ou `split_mode=expanding_walk_forward` e os parâmetros temporais da Fase 3.
- `temporal_protocol_json`: novo campo JSON no schema BigQuery para guardar o
  plano temporal completo do snapshot.

## Regras de segurança aplicadas

1. O holdout é sempre o bloco mais recente de sessões e não entra em folds de
   pesquisa.
2. Cada fold usa treino expansivo e teste externo posterior.
3. A calibração fica em janela própria, antes do teste externo.
4. Há embargo entre treino e calibração e entre calibração e teste externo.
5. Histórico insuficiente gera erro explícito, em vez de reduzir silenciosamente
   o protocolo.
6. O dataset persistido usa um split grosso (`research`/`locked_holdout`) para
   não induzir tuning acidental em janelas de fold sobrepostas.

## Validação local

- `PYTHONPATH=. pytest -q tests/test_neural_temporal_protocol.py tests/test_neural_training_dataset_function.py`
- `PYTHONPATH=. flake8`
- `PYTHONPATH=. pytest -q`

## Próximos passos

1. Fazer os jobs de treino consumirem `temporal_protocol_json` para executar a
   unidade `candidate × fold × seed`.
2. Persistir métricas por fold em `neural_fold_metrics`.
3. Garantir que leaderboard, HPO e advisor ignorem `locked_holdout` até o gate
   formal de holdout.
4. Conectar o avaliador econômico e o gate engine às janelas geradas por este
   plano.
