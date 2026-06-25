# Próximo passo — Redes neurais MUEN

**Última atualização:** 2026-06-24 23:30 UTC-3  
**Protocolo:** `neural_eod_protocol_v1`  
**Status:** ponto de parada operacional registrado

## Próximo passo atual

Fazer o treino/evaluador neural produzir `muen_economics` reais por `fold` e `seed`, para que o `neural_evolution_orchestrator` deixe de depender de payload sintético no `neural_model_registry`.

## Objetivo

Gerar evidência econômica completa para cada candidata neural, permitindo que o Gate Research MUEN use métricas materializadas em vez de bloquear por ausência de dados.

## Entregáveis esperados

1. Evoluir a etapa de treino/avaliação para executar avaliações por `fold_id`, `seed` e `cost_multiplier`.
2. Produzir `metrics_json.muen_economics` no registry com, no mínimo:
   - `protocol_version`;
   - `candidate_family_hash`;
   - `seed_count`;
   - `fold_metrics[]` compatível com `FoldEconomicMetrics`;
   - opcionalmente `family_evaluation`, quando a agregação já vier pronta.
3. Garantir que cada fold tenha comparação pareada contra champion/baseline econômico.
4. Validar que o orquestrador persiste:
   - `neural_fold_metrics`;
   - `neural_family_evaluations`;
   - `neural_gate_decisions` com `passed` ou `rejected` real.
5. Manter o fallback `muen_economics_missing` somente para execuções antigas ou incompletas.

## Critério de parada

O próximo ponto de parada será alcançado quando uma execução de teste do orquestrador receber `metrics_json.muen_economics` produzido pelo fluxo de treino/avaliação, persistir métricas por fold/família e emitir decisão de Gate Research sem o motivo `muen_economics_missing`.

## Observações operacionais

- Não promover modelo para holdout, shadow, paper ou produção apenas por `score_total`.
- O leaderboard continua sendo ordenação; o gate econômico decide avanço.
- Atualizar este arquivo sempre que o próximo passo das redes neurais mudar.
- Continuar registrando o trabalho executado em `docs/diario/registros1.md`.
