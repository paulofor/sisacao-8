# Próximo passo operacional das redes neurais — parte 2

## 2026-07-10 — Após implementação da guarda de evento neutro extremo

Foi executado o próximo passo herdado do arquivo antigo (`docs/diario/proximo-passo-redes.md`): antes de treinar nova TCN, foi implementada uma regra de abstenção configurável para eventos extremos de neutralidade.

Próximo passo operacional: após deploy de `neural_training` e `neural_evolution_orchestrator`, executar primeiro um dry-run de família tabular interpretável ou shadow pequena usando a guarda `neutral_event_min_*` (por exemplo calibrada no caso RCSL3: `neutral_event_min_abs_return_5d=0.18`, `neutral_event_min_financial_volume_z20=3.5`, `neutral_event_min_volume_ratio_20d=7.5`, `neutral_event_min_volatility_20d=0.05`). Exigir que o `model_version` contenha `nev_<hash>` e que o `training_request` propague os quatro thresholds antes de execução real.

Critério: comparar contra `bt3+regime`; só voltar para recorrentes/TCN se houver trades suficientes, remoção de caudas em eventos neutros extremos, `median_delta > 0`, `stable_across_seeds=true` e Gate MUEN aprovado. Manter sem promoção automática e sem Scheduler até aprovação operacional explícita.
