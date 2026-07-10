# Próximo passo operacional das redes neurais — parte 2

## 2026-07-10 — Shadows NEV tabulares rejeitadas pelo Gate MUEN

Foi concluída a validação pré-treino da guarda `neutral_event_min_*`: uma candidata `train_candidates=false` confirmou no BigQuery que o `training_request_json` propaga `neutral_event_min_abs_return_5d=0.18`, `neutral_event_min_financial_volume_z20=3.5`, `neutral_event_min_volume_ratio_20d=7.5` e `neutral_event_min_volatility_20d=0.05`, junto do `candidate_family_hash` com política `nev_rcsl3`.

Também foram executadas duas shadows pequenas reais, ambas sem promoção automática e sem Scheduler:

1. `tabular_bottleneck_mlp p50/m08/t35 + NEV`: execução técnica OK (`trained_count=1`, `failed_count=0`, `daily_return_count=3600`), mas Gate MUEN `rejected` por `trades_insuficientes`, `folds_positivos_insuficientes`, `nao_supera_champion_mediana` e `seeds_instaveis` (`total_trades=10`, `positive_folds=0`, `median_delta=0.0`, `stable_across_seeds=false`).
2. `tabular_bottleneck_mlp p48/m05/t50 + NEV`: execução técnica OK e maior cobertura (`total_trades=36`), mas Gate MUEN `rejected` por `folds_positivos_insuficientes`, `nao_supera_champion_mediana` e `seeds_instaveis` (`positive_folds=0`, `median_delta=-0.009692307692307705`, `max_drawdown=0.19564300000000015`).

Estado de prontidão: nenhuma rede neural está apta para teste em produção. A consulta operacional ao BigQuery mostrou `876` decisões no `neural_gate_decisions`, `0` aprovadas e `876` rejeitadas; o `neural_model_registry` contém apenas modelos `candidate`. Portanto, não promover modelos, não acionar Scheduler e não usar rede neural em produção.

Próximo passo operacional para fazer redes melhores: investigar por que as variantes NEV não geram folds positivos antes de insistir em arquiteturas mais complexas. Priorizar uma análise de `neural_daily_returns`/folds das duas famílias NEV por ticker e data para identificar se a guarda está removendo edge demais, se o target continua ruidoso em eventos neutros ou se os filtros `p/m/t` precisam virar busca calibrada por fold. Só depois testar nova família, preferencialmente em shadow com busca pequena de threshold/target e sem recorrentes/TCN até haver `median_delta > 0`, `positive_folds > 0`, trades suficientes e `stable_across_seeds=true`.
