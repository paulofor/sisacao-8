# Próximo passo — Redes neurais MUEN

**Última atualização:** 2026-06-27 19:18 UTC-3
**Protocolo:** `neural_eod_protocol_v1`
**Status:** ponto de parada operacional registrado

## Próximo passo atual

O código do treino/evaluador neural agora gera `metrics_json.muen_economics.fold_metrics` para novas candidatas usando predições dos splits não treino contra `buy_net_return`/`sell_net_return` e estresse de custo `1.0`/`1.5`. O próximo passo operacional é publicar a versão atual de `functions/neural_training`, executar um novo treino real para registrar uma candidata com o bloco `muen_economics`, confirmar o payload no `neural_model_registry`, executar `neural_champion_approval` em `mode=evaluate_candidate` com `dry_run=false`, validar a persistência em `neural_fold_metrics`, `neural_daily_returns` quando houver payload diário, `neural_family_evaluations` e `neural_gate_decisions`, e então chamar `approve_if_passed` primeiro em dry-run e depois em modo efetivo apenas se o Gate Research retornar `passed`.

## Objetivo

Fechar a primeira promoção governada de champion neural com evidência econômica MUEN persistida, decisão de Gate Research auditável e alteração de `neural_model_registry.status` para `approved` somente após autorização.

## Entregáveis esperados

1. Selecionar uma candidata real com `metrics_json.muen_economics.fold_metrics` preenchido por `fold_id`, `seed` e `cost_multiplier`.
2. Confirmar que o payload `metrics_json.muen_economics` no registry contém no mínimo:
   - `protocol_version`;
   - `candidate_family_hash`;
   - `seed_count`;
   - `fold_metrics[]` compatível com `FoldEconomicMetrics`;
   - `family_evaluation`, quando a agregação já vier pronta.
3. Garantir que cada fold tenha comparação pareada contra champion neural vigente ou baseline econômico líder quando ainda não existir champion.
4. Validar que `evaluate_candidate` e/ou o orquestrador persistem:
   - `neural_fold_metrics`;
   - `neural_daily_returns`, quando houver payload diário;
   - `neural_family_evaluations`;
   - `neural_gate_decisions` com `passed` ou `rejected` real.
5. Usar a rotina `evaluate_candidate` implementada em `functions/neural_champion_approval` para materializar as linhas MUEN e obter o `decision_id` do Gate Research.
6. Usar `approve_if_passed` para alterar `neural_model_registry.status` para `approved` somente com `decision_id` aprovado e autorização registrada; manter `muen_economics_missing` como bloqueio para execuções antigas ou incompletas.

## Critério de parada

O próximo ponto de parada será alcançado quando uma execução real de `evaluate_candidate` para uma candidata `keep_candidate` persistir métricas por fold/família/retorno diário quando disponível, emitir decisão de Gate Research sem `muen_economics_missing` e então executar `approve_if_passed` em dry-run e modo efetivo se o gate passar.

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

A rotina `functions/neural_champion_approval` implementa `evaluate_candidate`, `approve_if_passed` e `audit_current_champion`. O modo `evaluate_candidate` lê `metrics_json.muen_economics` do registry, materializa métricas MUEN e emite Gate Research; se o payload econômico estiver ausente, continua bloqueando com `muen_economics_missing`.

## Nota histórica: deploy do orquestrador — 2026-06-25

A falha de deploy do `neural_evolution_orchestrator` na revisão Cloud Run `neural-evolution-orchestrator-00026-duh` foi diagnosticada como erro de inicialização por dependência runtime ausente. O `requirements.txt` da função declarava apenas `google-cloud-bigquery`, mas o entrypoint importa `sisacao8.neural_muen`, que depende de `numpy` e `pandas`.

### Situação após 2026-06-27

A implementação local avançou o modo `evaluate_candidate` em `functions/neural_champion_approval`. A ação operacional atual está no topo deste arquivo: executar essa função contra candidata real com evidência `muen_economics`, validar BigQuery e só então chamar `approve_if_passed` se o gate passar.


## Execução do próximo passo no código — 2026-06-27 09:42 UTC-3

`functions/neural_champion_approval` passou a executar `evaluate_candidate` sobre evidência econômica MUEN já presente no registry. A próxima ação operacional é acionar essa função contra uma candidata real com `dry_run=false`, validar as linhas persistidas no BigQuery e usar o `decision_id` retornado no modo `approve_if_passed` se o gate passar.


## Diagnóstico de execução — 2026-06-27 14:55 UTC-3

Foi tentada a execução do próximo passo contra a Cloud Function publicada `neural_champion_approval` usando `evaluate_candidate` para `neural_eod_mlp_evo2_20260624_mutation_01`. A função publicada retornou `status=blocked` com `reason=evaluate_candidate_requires_economic_evaluator_integration`, indicando que o deploy em produção ainda está anterior à implementação local que lê `metrics_json.muen_economics`. Também foi tentada consulta via MCP HTTP/JSON-RPC para localizar candidatas com `muen_economics`, mas o endpoint alternou `503`/timeout e sessão inválida; a API publicada de treinos mostrou candidatos com `metricsJson` básico de treino/teste, sem evidência econômica MUEN no payload retornado.

**Ponto de parada atualizado em 2026-06-27 19:03 UTC-3:** a função publicada `neural_champion_approval` já executa a implementação atual de `evaluate_candidate`, mas a candidata real testada continua sem `metrics_json.muen_economics`. Agora falta garantir pelo menos uma candidata com `metrics_json.muen_economics.fold_metrics`; sem esse payload econômico, o gate econômico não consegue materializar decisão auditável nem aprovar champion.


## Verificação de publicação — 2026-06-27 19:03 UTC-3

Foi verificado por chamada HTTP produtiva que `https://us-east1-ingestaokraken.cloudfunctions.net/neural_champion_approval` já está publicada com a implementação atual de `evaluate_candidate`: a resposta para `neural_eod_mlp_evo2_20260624_mutation_01` foi `status=blocked` com `reason=muen_economics_missing`, não mais `evaluate_candidate_requires_economic_evaluator_integration`. Consulta BigQuery via MCP HTTP/JSON-RPC ao registry confirmou que as 20 linhas recentes de candidatas continuam com `muen_protocol` e `fold_count` nulos. Também foi verificado que o Scheduler `neural-evolution-daily` existe e está `ENABLED` em `ingestaokraken/us-east1`; não existe job `neural-champion-approval-daily`, e não foi recomendado criá-lo enquanto não houver payload econômico MUEN para avaliar.


## Implementação da geração de `muen_economics` — 2026-06-27 19:18 UTC-3

O próximo passo foi implementado no código: `sisacao8.neural_training.build_muen_economics_from_predictions` calcula evidência econômica MUEN a partir das predições de validação/teste e dos retornos realizados `buy_net_return`/`sell_net_return`, gerando folds por split e multiplicador de custo. `train_baseline_mlp` passa a anexar esse payload dentro de `metrics["muen_economics"]` antes de registrar a candidata. O deploy e a execução produtiva do novo treino ainda são necessários para que uma candidata real no BigQuery carregue o payload.
