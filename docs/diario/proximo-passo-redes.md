# Próximo passo — Redes neurais MUEN

**Última atualização:** 2026-06-25 07:42 UTC-3
**Protocolo:** `neural_eod_protocol_v1`
**Status:** ponto de parada operacional registrado

## Próximo passo atual

Conectar a rotina `evaluate_candidate` ao avaliador econômico real para produzir `muen_economics` por `fold`, `seed` e cenário de custo; a rotina `approve_if_passed` já existe para promover `approved` somente após Gate Research aprovado.

## Objetivo

Gerar evidência econômica completa para cada candidata neural, persistir o Gate Research MUEN real e permitir que uma candidata aprovada seja promovida de `candidate` para `approved` com trilha auditável.

## Entregáveis esperados

1. Criar rotina `evaluate_candidate` para executar avaliações por `fold_id`, `seed` e `cost_multiplier`.
2. Produzir `metrics_json.muen_economics` real no registry ou payload equivalente consumido pelo orquestrador, com no mínimo:
   - `protocol_version`;
   - `candidate_family_hash`;
   - `seed_count`;
   - `fold_metrics[]` compatível com `FoldEconomicMetrics`;
   - `family_evaluation`, quando a agregação já vier pronta.
3. Garantir que cada fold tenha comparação pareada contra champion neural vigente ou baseline econômico líder quando ainda não existir champion.
4. Validar que o orquestrador persiste:
   - `neural_fold_metrics`;
   - `neural_daily_returns`;
   - `neural_family_evaluations`;
   - `neural_gate_decisions` com `passed` ou `rejected` real.
5. Usar a rotina `approve_if_passed` implementada em `functions/neural_champion_approval` para alterar `neural_model_registry.status` para `approved` somente com `decision_id` aprovado e autorização registrada.
6. Manter o fallback `muen_economics_missing` somente para execuções antigas ou incompletas.

## Critério de parada

O próximo ponto de parada será alcançado quando uma execução real selecionar uma candidata `keep_candidate`, produzir `muen_economics` real por fold/seed/custo, persistir métricas por fold/família/retorno diário, emitir decisão de Gate Research sem `muen_economics_missing` e então executar `approve_if_passed` em dry-run e modo efetivo.

## Observações operacionais

- Não promover modelo para holdout, shadow, paper ou produção apenas por `score_total`.
- O leaderboard continua sendo ordenação; o gate econômico decide avanço.
- Atualizar este arquivo sempre que o próximo passo das redes neurais mudar.
- Continuar registrando o trabalho executado em `docs/diario/registros1.md`.

## Nota de interface — 2026-06-25 00:02 UTC-3

A tela `Redes neurais — Jornada passo a passo` agora explica visualmente o bloqueio do passo `Baselines` com uma checklist de gate: baseline econômico medido, champion aprovado, challenger avaliada e gate econômico persistido. O próximo passo operacional acima permanece o mesmo; a mudança foi de clareza visual para evitar que métricas de baseline sejam interpretadas como aprovação.


## Processo de aprovação de champion — 2026-06-25 07:21 UTC-3

Foi definido o processo operacional em `docs/implementacao/processo-aprovacao-champion-neural-muen.md`. O documento separa claramente geração de candidatas, avaliação econômica, gate, revisão de governança e atualização do registry para `approved`.


## Implementação parcial do processo — 2026-06-25 07:42 UTC-3

A rotina `functions/neural_champion_approval` implementa `approve_if_passed` e `audit_current_champion`. O modo `evaluate_candidate` permanece bloqueado explicitamente até ser conectado ao avaliador econômico real, evitando aprovação baseada em payload incompleto.
