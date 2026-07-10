# Próximo passo operacional das redes neurais — parte 2

## 2026-07-10 — Dry-run tabular com guarda de evento neutro extremo concluído

O primeiro dry-run da família tabular interpretável com a guarda `neutral_event_min_*` foi executado no endpoint publicado `neural_evolution_orchestrator` em 2026-07-10. A chamada retornou HTTP 200 com `status=ok`, `dry_run=true`, `candidate_count=1`, snapshot `neural_eod_training_dataset_2026-07-08_6c894390` e candidata `neural_eod_nev_guard_20260710_tabular_bottleneck_mlp_p50_m08_t35_nev_b4f5a5_01`, confirmando que o `model_version` produtivo inclui o sufixo rastreável `nev_<hash>`.

Próximo passo operacional: antes de qualquer treino real, validar que o `training_request` montado pelo orquestrador propaga os quatro thresholds `neutral_event_min_abs_return_5d=0.18`, `neutral_event_min_financial_volume_z20=3.5`, `neutral_event_min_volume_ratio_20d=7.5` e `neutral_event_min_volatility_20d=0.05`. Como o dry-run HTTP não grava nem retorna o `training_request` completo, fazer essa confirmação por configuração persistida/controlada ou por chamada real mínima cuidadosamente observada; só depois liberar a execução shadow pequena.

Critério para avançar à execução real pequena: `training_request` contém os quatro thresholds, `candidate_family_hash` e `model_version` contêm a política `nev_<hash>`, a execução permanece sem promoção automática e sem Scheduler. Após a rodada real pequena, comparar contra `bt3+regime`; só voltar para recorrentes/TCN se houver trades suficientes, remoção de caudas em eventos neutros extremos, `median_delta > 0`, `stable_across_seeds=true` e Gate MUEN aprovado.
