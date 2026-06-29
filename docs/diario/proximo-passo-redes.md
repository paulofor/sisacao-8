# Próximo passo — Redes neurais MUEN

**Última atualização:** 2026-06-28 01:05 UTC-3
**Última atualização:** 2026-06-27 22:47 UTC-3
**Última atualização:** 2026-06-27 22:36 UTC-3
**Protocolo:** `neural_eod_protocol_v1`
**Status:** ponto de parada operacional registrado

## Próximo passo atual

O código do treino/evaluador neural agora gera `metrics_json.muen_economics.fold_metrics` para novas candidatas usando predições dos splits não treino contra `buy_net_return`/`sell_net_return` e estresse de custo `1.0`/`1.5`. Antes de rodar o novo treino real, é necessário aplicar no BigQuery o schema v2 do dataset neural: as colunas `log_return_1d`, `log_return_5d`, `log_return_10d`, `log_return_20d`, `log_financial_volume` e `log_volume` em `neural_eod_training_dataset`, além da tabela `neural_dataset_manifests`. Depois disso, executar `neural_training_dataset` para gerar um snapshot v2, rodar `neural_training` apontando para esse snapshot, confirmar o payload no `neural_model_registry`, executar `neural_champion_approval` em `mode=evaluate_candidate` com `dry_run=false`, validar a persistência em `neural_fold_metrics`, `neural_daily_returns` quando houver payload diário, `neural_family_evaluations` e `neural_gate_decisions`, e então chamar `approve_if_passed` primeiro em dry-run e depois em modo efetivo apenas se o Gate Research retornar `passed`.

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


## Diagnóstico de schema do dataset v2 — 2026-06-27 22:04 UTC-3

A candidata `neural_eod_mlp_muen_codex_20260628_030718` já passou por `evaluate_candidate` e recebeu decisão `rejected` (`gate_4f4ef2b62065636f969929ec3007fb47`), portanto não executar `approve_if_passed` para ela. A próxima ação não deve ser repetir manualmente dataset/treino/gate; o fluxo recorrente deve ser automatizado pelo Cloud Scheduler `neural-evolution-daily` chamando `neural_evolution_orchestrator` com `strategy=deterministic_phase2`, para gerar/mutar novas candidatas, chamar `neural_training`, materializar métricas MUEN e emitir novas decisões de gate. `approve_if_passed` permanece manual/governado apenas para decisões `passed`.

## Visibilidade das tentativas MUEN — 2026-06-28 01:05 UTC-3

A tela de evolução neural foi preparada para acompanhamento operacional das tentativas: o backend passa a expor `/ops/neural/gate-decisions`, consultando `neural_gate_decisions` com métricas agregadas de `neural_family_evaluations`, e o frontend passa a exibir a seção `Últimas tentativas MUEN` na aba `Redes neurais — Evolução`. Após deploy do backend/frontend, o usuário poderá acompanhar na tela as decisões `passed`/`rejected`, `decision_id`, critérios reprovados, folds/seeds, delta de expectancy, drawdown e trades. O próximo passo operacional continua sendo manter o Scheduler `neural-evolution-daily` acionando `neural_evolution_orchestrator`; a aprovação `approve_if_passed` segue manual/governada somente quando uma tentativa aparecer como `passed`.
A execução produtiva de `neural_training_dataset` retornou 500 porque a tabela `cotacao_intraday.neural_eod_training_dataset` ainda não tinha todas as colunas v2 geradas pelo código publicado. Os logs via MCP/Cloud Run confirmaram rejeição BigQuery por campos ausentes, incluindo `log_return_1d`, `log_volume`, `trade_side` e `exit_price` durante tentativas feitas com a migração parcial. Consulta posterior ao `INFORMATION_SCHEMA` confirmou que as 19 colunas v2 esperadas já existem na tabela produtiva e que `neural_dataset_manifests` também existe. Uma chamada controlada ainda retornou 500, e os logs disponíveis via MCP permaneceram dominados por stack traces antigos da migração parcial; por isso o próximo passo imediato passa a ser publicar `functions/neural_training_dataset` com o hardening que filtra a carga JSON para o contrato BigQuery (`TRAINING_DATASET_COLUMNS`) e com o retorno JSON de erro (`status`, `error_type`, `message`), repetir a materialização com um novo `DATASET_SNAPSHOT` e usar a mensagem retornada pelo `curl` para fechar a causa remanescente.
A execução produtiva de `neural_training_dataset` retornou 500 porque a tabela `cotacao_intraday.neural_eod_training_dataset` ainda não tinha todas as colunas v2 geradas pelo código publicado. Os logs via MCP/Cloud Run confirmaram rejeição BigQuery por campos ausentes, incluindo `log_return_1d`, `log_volume`, `trade_side` e `exit_price` durante tentativas feitas com a migração parcial. Consulta posterior ao `INFORMATION_SCHEMA` confirmou que as 19 colunas v2 esperadas já existem na tabela produtiva e que `neural_dataset_manifests` também existe. Uma chamada controlada ainda retornou 500, e os logs disponíveis via MCP permaneceram dominados por stack traces antigos da migração parcial; por isso o próximo passo imediato passa a ser publicar `functions/neural_training_dataset` com o hardening que filtra a carga JSON para o contrato BigQuery (`TRAINING_DATASET_COLUMNS`) e repetir a materialização com um novo `DATASET_SNAPSHOT`.

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

## Nota de visibilidade na aba Treinos — 2026-06-28 15:05 UTC-3

A aba `Redes neurais — Treinos` passou a exibir também as decisões recentes do Gate MUEN, incluindo rejeições e critérios reprovados, para deixar claro que candidatas com status `candidate` no registry podem já ter sido analisadas e bloqueadas pelo gate econômico. O próximo passo operacional não mudou: manter a geração recorrente de candidatas via orquestrador/Scheduler e reservar `approve_if_passed` apenas para decisões `passed`.

## Diagnóstico de parada das análises — 2026-06-28 16:03 UTC-3

As análises MUEN não pararam porque o Scheduler deixou de executar. A última decisão persistida visível na tela é de 2026-06-28 08:31:26 UTC (05:31 em America/Sao_Paulo), mas logs posteriores da Cloud Function `neural_evolution_orchestrator` mostram chamadas às 14:30 e 15:30 BRT retornando HTTP 500. A causa confirmada nos logs é `ValueError: No neural evolution candidates were generated`, ou seja, o orquestrador foi acionado, mas não conseguiu gerar uma candidata inédita antes de gravar nova execução/decisão.

Próximo passo imediato: corrigir a estratégia de geração recorrente para lidar com grid esgotado/deduplicação total — por exemplo ampliar o espaço de mutações/seeds, relaxar/fazer reset controlado do filtro de hashes por rodada quando apropriado, ou retornar status controlado sem 500 — e depois disparar nova execução para confirmar que novas linhas aparecem em `neural_gate_decisions`.

## Correção local para grid esgotado — 2026-06-28 16:12 UTC-3

Foi implementado fallback no orquestrador neural para quando a Fase 2 não consegue gerar mutações inéditas porque todos os hashes do grid atual já existem. Nessa situação, o código passa a criar repetições dos finalistas com seeds inéditas, validando contra `existing_hashes`, em vez de abortar a execução com HTTP 500 antes de gravar nova decisão.

Próximo passo imediato: publicar `functions/neural_evolution_orchestrator` com essa correção e disparar/aguardar o Scheduler `neural-evolution-daily`; a validação operacional esperada é observar novas linhas em `neural_gate_decisions` após uma execução bem-sucedida.

## Ajuste do fallback para novas arquiteturas — 2026-06-28 16:27 UTC-3

A correção local foi refinada: quando a Fase 2 esgotar as mutações comuns, o orquestrador agora deve tentar primeiro novas arquiteturas MLP derivadas dos finalistas (mais largas, mais estreitas, mais profundas ou mais rasas), respeitando orçamento de camadas/parâmetros e `existing_hashes`. Repetições com seeds inéditas permanecem como fallback secundário, útil para medir estabilidade, mas não são mais a primeira resposta ao grid esgotado.

Próximo passo imediato: publicar `functions/neural_evolution_orchestrator`, acionar/aguardar o Scheduler e verificar se as novas linhas em `neural_candidate_configs`/`neural_gate_decisions` incluem `candidate_source=architecture_variant` antes de `seed_repeat_fresh`.

## Ajuste solicitado de cadência do Scheduler — 2026-06-28 22:52 UTC-3

Foi confirmado via MCP HTTP/JSON-RPC que o Scheduler `neural-evolution-daily` está ativo em `ingestaokraken/us-east1` com agenda atual `30 * * * *`, ou seja, uma execução por hora no minuto 30 em `America/Sao_Paulo`. A alteração desejada é `*/30 * * * *`, para executar de meia em meia hora.

A tentativa de aplicar diretamente pelo MCP falhou com `PERMISSION_DENIED` porque a service account `codex-openai@ingestaokraken.iam.gserviceaccount.com` não possui `cloudscheduler.jobs.update`. Próximo passo imediato: conceder permissão de update no Cloud Scheduler a essa conta ou executar, com uma conta autorizada, o comando de update documentado em `docs/neural_evolution_orchestrator_scheduler.md`; em seguida validar por `cloud_scheduler_job`/`gcloud scheduler jobs describe` que o schedule ficou `*/30 * * * *`.

## Orientação para novas famílias neurais — 2026-06-29 07:45 UTC

Estado confirmado: o leaderboard publicado contém 100 avaliações, com 56 candidatas determinísticas, 28 por mutação e 16 `architecture_variant`; portanto a evolução já começou a variar topologias MLP, mas ainda não testa famílias radicalmente diferentes de MLP.

Próximo passo recomendado: não esperar para pesquisa. Depois de publicar/validar o fallback `architecture_variant`, abrir uma Fase 3 experimental com orçamento pequeno para novas famílias neurais em modo shadow/pesquisa, mantendo o MLP atual como champion e usando MUEN para comparação. Priorizar 2 ou 3 famílias no máximo inicialmente, sem promoção automática: por exemplo MLP residual/tabular melhorada, CNN/TCN temporal curta ou GRU/LSTM leve apenas se houver dataset sequencial adequado.

## Fase 3 implementada localmente — 2026-06-29 07:52 UTC

A Fase 3 experimental foi implementada no código para gerar e treinar novas famílias tabulares em modo pesquisa/shadow: `residual_mlp`, `wide_deep_mlp` e `tabular_bottleneck_mlp`. O orquestrador passa a aceitar `strategy=phase3_new_families`/`phase3`/`new_families`, e o treino passa a respeitar `architecture_type` no payload.

Próximo passo imediato: publicar `functions/neural_training` e `functions/neural_evolution_orchestrator`; executar primeiro dry-run com `strategy=phase3_new_families`, `budget.max_trials=2` ou `3` e `train_candidates=false`/`dry_run=true`; depois executar uma rodada treinada pequena em shadow/pesquisa, validar registros em `neural_candidate_configs`, `neural_model_registry`, `neural_candidate_evaluations` e decisões MUEN, sem chamar `approve_if_passed` salvo decisão `passed` e aprovação humana explícita.

## Scheduler para Fase 3 — 2026-06-29 07:58 UTC

Não é obrigatório criar novo Cloud Scheduler para a Fase 3, porque `neural_evolution_orchestrator` já escolhe a estratégia pelo payload (`strategy=phase3_new_families`). Porém, por segurança operacional, não substituir o payload recorrente do `neural-evolution-daily` sem decisão explícita: ele deve continuar cuidando da Fase 2/incremental do MLP.

Próximo passo recomendado: após publicar `functions/neural_training` e `functions/neural_evolution_orchestrator`, rodar primeiro um `curl` manual com `dry_run=true` e `strategy=phase3_new_families`; se a rodada treinada pequena passar pelos checks, criar um Scheduler separado e controlado, por exemplo `neural-evolution-phase3-weekly`, inicialmente pausado ou semanal. Não automatizar `approve_if_passed`.

## Confirmação do agendamento existente — 2026-06-29 08:02 UTC

Foi confirmado via MCP HTTP/JSON-RPC que o Cloud Scheduler `neural-evolution-daily` existe em `ingestaokraken/us-east1`, está `ENABLED` e roda `*/30 * * * *` em `America/Sao_Paulo`, ou seja, de 30 em 30 minutos. A última tentativa vista foi `2026-06-29T08:01:19.716573Z`.

O payload atual do job chama `neural_evolution_orchestrator` com `strategy=deterministic_phase2`, `budget.max_trials=1`, `max_runtime_minutes=45` e `phase2.include_seed_repeats=false`; portanto o Scheduler existente está rodando Fase 2, não Fase 3. Próximo passo para Fase 3 permanece: rodar primeiro dry-run/manual com `strategy=phase3_new_families` e só criar Scheduler separado se houver decisão de recorrência controlada.

## Teste manual da Fase 3 — 2026-06-29 08:08 UTC

Roteiro documentado em `docs/neural_evolution_orchestrator_scheduler.md`: depois do deploy, executar primeiro `curl` com `dry_run=true`, `strategy=phase3_new_families` e `budget.max_trials=3`; validar `status=ok`, `dry_run=true` e candidatas `neural_eod_phase3_*`; só então executar uma rodada real mínima com `max_trials=1`. A validação deve ser feita pela API `/api/ops/neural/evolution/leaderboard` e, se necessário, por consulta MCP/BigQuery em `neural_candidate_configs`. Não automatizar `approve_if_passed`.

## Dry-run Fase 3 indica deploy desatualizado — 2026-06-29 08:14 UTC

O teste do usuário com `strategy=phase3_new_families` retornou `neural_eod_mlp_evo1_20260629_*`, e o `curl` local reproduziu o mesmo comportamento. Isso indica que a Cloud Function publicada ainda não contém a implementação local da Fase 3; se estivesse atualizada, o dry-run deveria indicar `candidate_sources=["phase3_family"]`, `architecture_types` com novas famílias e candidatos `neural_eod_phase3_*`. Próximo passo: publicar `functions/neural_evolution_orchestrator` e `functions/neural_training`, repetir o dry-run e só executar treino real se esses campos confirmarem Fase 3.

## Resultado do teste manual criado — 2026-06-29 08:18 UTC

A execução real `neural_evolution_20260629_081013_8114097c` foi criada e avaliada, mas não como Fase 3 real: ela aparece com `strategy=phase3_new_families`, porém `candidateSource=deterministic`, `modelId=neural_eod_mlp`, `modelVersion=neural_eod_mlp_evo1_20260629_01` e arquitetura `type=mlp`. O BigQuery/MCP confirmou avaliação `decision=reject` e gate `rejected`. Próximo passo: não repetir treino real; redeployar `functions/neural_evolution_orchestrator` e `functions/neural_training`, repetir dry-run e só avançar quando vier `candidate_sources=["phase3_family"]` e prefixo `neural_eod_phase3_`.

## Comando Scheduler Fase 3 30 minutos — 2026-06-29 08:23 UTC

Foi documentado o comando para criar `neural-evolution-phase3-30m` com agenda `*/30 * * * *`, payload `strategy=phase3_new_families` e `budget.max_trials=1`. Só executar depois de redeployar as funções e confirmar em dry-run que a resposta traz `candidate_sources=["phase3_family"]` e prefixo `neural_eod_phase3_`; caso contrário, o Scheduler repetirá o fluxo MLP antigo.
