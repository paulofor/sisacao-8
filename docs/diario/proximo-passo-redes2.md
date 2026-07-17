# Próximo passo operacional das redes neurais — parte 2

## 2026-07-12 — Automatizar busca de challenger mantendo Apolo em observação

Agora que existe um champion aprovado (`Apolo NEV`) e o pipeline `neural_eod_predictions`/`eod_signals` já materializa predições, o próximo passo recomendado é **não depender de execução manual aqui no chat**. O melhor caminho é criar/ajustar uma rotina automatizada de busca de challengers em shadow, mantendo a promoção final manual e governada.

### Trilha A — observar o Apolo NEV

Manter o Apolo NEV em shadow/operacional controlado por pelo menos 5 pregões, sem capital real:

- confirmar diariamente se `neural_eod_predictions` gravou predições para o último pregão e `valid_for` correto;
- confirmar se `eod_signals` gerou sinais ou se houve abstenção (`HOLD`/sem BUY/SELL);
- monitorar a aba `Champion NEV`, especialmente o alerta de abstenção, sinais em tickers bloqueados (`ONCO3`, `VVEO3`, `AMBP3`), incidentes e falhas de scheduler;
- comparar as predições/sinais com retornos realizados no pregão seguinte para avaliar se o comportamento em produção está coerente com o Gate MUEN.

### Trilha B — automatizar busca de challenger

Criar ou ajustar uma rotina recorrente de evolução neural para buscar redes melhores que o Apolo:

1. Rodar fora do horário crítico de ingestão/sinais, por exemplo madrugada ou janela de baixa carga.
2. Gerar poucos candidatos por rodada (`max_trials` baixo) para evitar custo e ruído operacional.
3. Avaliar cada candidato contra o Apolo como benchmark, não contra um baseline antigo.
4. Persistir métricas MUEN, taxa de abstenção, coverage, drawdown, trades e estabilidade por seed/fold.
5. Alertar quando um challenger passar no Gate MUEN, mas **não promover automaticamente**.
6. Exigir aprovação manual explícita para substituir o champion.

Payload recomendado para a rotina recorrente:

```json
{
  "strategy": "apolo_challenger_shadow",
  "budget": {"max_trials": 1, "random_seed": 20260712},
  "train_candidates": true,
  "reason": "scheduled-apolo-challenger-shadow"
}
```

Cron sugerido, se criado por operador autorizado: `30 2 * * 2-6` em `America/Sao_Paulo`, para rodar de terça a sábado de madrugada após a materialização EOD do pregão anterior.

### Critérios para aceitar um challenger

- Não afrouxar thresholds apenas para forçar sinais; a abstenção é aceitável quando a confiança direcional não passa na régua operacional.
- Priorizar edge econômico superior, menor abstenção improdutiva, boa calibração, robustez por folds/seeds e drawdown controlado.
- Toda troca de champion deve continuar governada: Gate MUEN aprovado, auditoria, aprovação manual explícita e registro no diário.

Critério de parada/decisão: depois de 5 pregões de observação, revisar taxa de abstenção, sinais gerados, retornos realizados, incidentes e qualidade dos challengers. Se o Apolo apenas abstiver sem gerar valor operacional, focar em melhorar dataset/features/thresholds calibrados; se surgirem sinais bons e estáveis, manter shadow por mais pregões antes de discutir qualquer uso com capital real.

### Acompanhamento da Trilha B pelo backend

Enquanto não houver uma tela dedicada para `apolo_challenger_shadow`, acompanhar a Trilha B pelo backend usando estes endpoints publicados:

1. `GET http://34.194.252.70/api/ops/neural/champion-monitoring` — baseline do Apolo: champion aprovado, decisão MUEN, predições recentes, sinais e eventual abstenção.
2. `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard` — ranking das candidatas geradas pelo orquestrador; filtrar no payload por `strategy == "apolo_challenger_shadow"` e comparar `scoreTotal`, `scoreDirectionalPrecision`, `scoreCoverage`, `scoreStability` e `decision`.
3. `GET http://34.194.252.70/api/ops/neural/gate-decisions` — auditoria MUEN das candidatas; procurar `candidateFamilyHash` das famílias da Trilha B e verificar `passed`, `failedCriteria`, `medianDeltaExpectancyVsChampion`, `maxDrawdown`, `totalTrades` e estabilidade por seeds/folds.
4. `GET http://34.194.252.70/api/ops/neural/training-runs` — registry/treinos; confirmar se as candidatas `apolo_challenger_shadow` chegaram a treinar, status (`candidate`, `approved`, `rejected`) e métricas fora da amostra.

Comandos rápidos para operador:

```bash
curl -sS 'http://34.194.252.70/api/ops/neural/evolution/leaderboard' \
  | python3 - <<'PY'
import json, sys
rows = json.load(sys.stdin)
for r in rows:
    if r.get('strategy') == 'apolo_challenger_shadow':
        print(r.get('createdAt'), r.get('modelVersion'), r.get('scoreTotal'), r.get('decision'))
PY

curl -sS 'http://34.194.252.70/api/ops/neural/gate-decisions' \
  | python3 - <<'PY'
import json, sys
rows = json.load(sys.stdin)
for r in rows[:50]:
    h = (r.get('candidateFamilyHash') or '').lower()
    if 'apolo' in h or 'challenger' in h or 'tabular_bottleneck' in h or 'wide_deep' in h:
        print(r.get('decidedAt'), r.get('candidateFamilyHash'), r.get('passed'), r.get('failedCriteria'))
PY
```

Se esses filtros retornarem vazio logo após alterar/criar o Scheduler, isso não é necessariamente erro: primeiro confirme que o Scheduler disparou e que o `neural_evolution_orchestrator` registrou candidatos; depois verifique `training-runs` e `gate-decisions`. A melhoria recomendada para a próxima evolução de backend é criar um endpoint dedicado, por exemplo `GET /ops/neural/challenger-shadow?strategy=apolo_challenger_shadow`, agregando em uma única resposta champion atual, últimas rodadas, candidatos, decisões MUEN e deltas contra o Apolo.

### Acompanhamento da Trilha B pelo frontend

Correção operacional: para acompanhar pela interface web, abrir `http://34.194.252.70/` e usar o menu lateral **Redes neurais**. A leitura recomendada é:

1. **Champion NEV** — acompanhar o Apolo aprovado: Gate MUEN, predições recentes, sinais gerados e alerta de abstenção quando há predições sem BUY/SELL.
2. **Evolução** — acompanhar a Trilha B propriamente dita: seção **Últimas tentativas MUEN** para ver decisões `Aprovado`/`Rejeitado`, critérios reprovados, folds, seeds, delta de expectancy, drawdown, trades e data; depois conferir **Famílias e leaderboard** para ranking das famílias/candidatas.
3. **Treinos** — confirmar se o Scheduler realmente criou/treinou novas redes, observar o gráfico diário de redes criadas x testadas, status de cada modelo e métricas de treino/validação/teste.
4. **Visão geral** — leitura executiva para saber se existe candidata em estoque, melhor índice de pesquisa e próximos passos, sem tratar score como aprovação.

Para a Trilha B, a ordem prática na tela é: clicar **Atualizar**, abrir **Evolução**, procurar uma tentativa MUEN recente gerada depois do horário do Scheduler, verificar se alguma veio `Aprovado`; se sim, abrir **Treinos** para auditar o modelo e, por fim, comparar com **Champion NEV**. Se aparecer tudo vazio logo após a mudança do Scheduler, aguardar a próxima janela de execução e confirmar em **Treinos** se algum artefato novo foi criado.

## 2026-07-14 — Estado atual da comparação contra Apolo

Verificação operacional mais recente: o Apolo NEV permanece como único modelo aprovado pelo Gate MUEN entre as decisões disponíveis no backend. Há candidatas com expectativa mediana pontualmente superior ao champion, mas elas continuam reprovadas por risco/robustez, especialmente drawdown excessivo e instabilidade de seeds.

Próximo passo mantido: continuar a Trilha B (`apolo_challenger_shadow`) buscando challengers, mas tratar redes como `neural_eod_mlp_evo2_20260709_diversity_01` apenas como candidatas de pesquisa até reduzirem drawdown e comprovarem estabilidade por seeds/folds. Não promover nenhuma rede acima do Apolo sem novo `passed=true` no Gate MUEN e aprovação manual explícita.

## 2026-07-15 — Refinar candidatas promissoras antes de mudar arquitetura ampla

Próximo passo recomendado: manter Apolo como champion e abrir uma trilha curta de refinamento das famílias que já demonstraram algum sinal econômico, em vez de trocar amplamente a estrutura de criação das redes.

Prioridade operacional:
1. Refinar `wide_deep` e `tabular_bottleneck` próximas ao Apolo, além da família `neural_eod_mlp_evo2_20260709_diversity_01`, porque já apareceram como candidatas com potencial, mas falharam por risco/robustez.
2. Variar poucos parâmetros por rodada: `min_directional_probability`, `min_directional_margin`, `max_trades_per_fold`, bloqueio de tickers problemáticos, regularização/dropout e seeds.
3. Exigir que qualquer melhoria reduza drawdown e estabilize seeds/folds; não basta aumentar expectancy pontual.
4. Só partir para mudanças estruturais grandes se esse refinamento falhar por múltiplos ciclos, mantendo sempre comparação contra o Apolo e promoção manual após `passed=true` no Gate MUEN.

## 2026-07-15 — Estratégia `apolo_challenger_refinement` implementada

A sugestão foi materializada no código como a estratégia `apolo_challenger_refinement` do `neural_evolution_orchestrator`. Ela deve ser usada como próxima rodada da Trilha B quando o operador quiser treinar challengers mais conservadores contra o Apolo.

Payload recomendado para execução controlada:

```json
{
  "strategy": "apolo_challenger_refinement",
  "budget": {"max_trials": 3, "random_seed": 20260715},
  "train_candidates": true,
  "reason": "manual-apolo-challenger-refinement"
}
```

Critério de parada: não promover automaticamente. Acompanhar `gate-decisions`, `evolution/leaderboard` e `training-runs`; só discutir troca de champion se algum refinamento vier com `passed=true`, drawdown menor/aceitável e seeds/folds estáveis contra o Apolo.

## 2026-07-15 — Ativar evolução natural do refinamento

Estado confirmado: o Scheduler `neural-evolution-daily` continua ativo, mas ainda aponta para `strategy=apolo_challenger_shadow` com `max_trials=1`. Portanto, o refinamento novo não evolui automaticamente até o deploy do código e a alteração/criação do Scheduler.

Próximo passo operacional recomendado:
1. Fazer deploy da versão que contém `apolo_challenger_refinement` em `neural_evolution_orchestrator`.
2. Escolher entre:
   - alterar `neural-evolution-daily` para `strategy=apolo_challenger_refinement`; ou
   - criar um Scheduler separado para refinamento, preservando o shadow atual.
3. Usar payload com `max_trials=3`, `train_candidates=true` e promoção manual somente após `passed=true` no Gate MUEN.
4. Após a primeira execução, conferir `gate-decisions`, `evolution/leaderboard` e `training-runs` antes de discutir qualquer nova alteração.

## 2026-07-15 — Diagnóstico antes de reexecutar sinais do Apolo

Estado do dia: o Apolo não gerou sinais. A execução agendada de `eod_signals` ocorreu, mas os logs indicaram `Sem candles disponíveis para 2026-07-14`; no BigQuery, as últimas predições neurais disponíveis continuam com `valid_for=2026-07-14` e todas `HOLD`.

Próximo passo operacional imediato:
1. Validar no BigQuery se `cotacao_ohlcv_diario`/tabela diária esperada recebeu candles de `2026-07-14`.
2. Se os candles estiverem ausentes, corrigir/reexecutar a consolidação diária antes das redes.
3. Depois dos candles confirmados, reexecutar `neural_eod_predictions` para `date_ref=2026-07-14` e em seguida `eod_signals` com `signal_source=neural`.
4. Só interpretar ausência de BUY/SELL como abstenção do Apolo se houver predições novas para `valid_for=2026-07-15`; caso contrário, tratar como bloqueio de dados/candles.

## 2026-07-15 — Causa confirmada pelo MCP: candles diários ausentes

Diagnóstico confirmado via MCP: o bloqueio de sinais do Apolo em `2026-07-15` veio da ausência de candles diários de `2026-07-14` em `cotacao_ohlcv_diario`. A B3 retornou 404 para `COTAHIST_D14072026.ZIP`, o modo estrito rejeitou arquivos de datas anteriores e `allow_offline_fallback=false` impediu fallback.

Próximo passo operacional revisado:
1. Decidir se a correção será aguardar/publicar o arquivo oficial da B3 e reexecutar `get_stock_data` para `2026-07-14`, ou habilitar/usar uma rotina controlada de fallback/consolidação a partir de dados intraday, sabendo que `cotacao_b3` tem apenas 47 tickers no dia.
2. Após popular `cotacao_ohlcv_diario` para `2026-07-14`, reexecutar `neural_eod_predictions` com `date_ref=2026-07-14`.
3. Se forem geradas predições para `valid_for=2026-07-15`, reexecutar `eod_signals` neural para `date_ref=2026-07-14`.
4. Só interpretar o resultado como abstenção do Apolo se as predições novas existirem e vierem `HOLD`/sem BUY/SELL; enquanto os candles diários estiverem ausentes, tratar como falha de dados upstream.

## 2026-07-15 — Correção aplicada e Apolo reprocessado

A carga diária ausente foi corrigida por reexecução manual de `get_stock_data` para `date_ref=2026-07-14`. Depois disso, `neural_eod_predictions` gerou 150 predições do Apolo para `valid_for=2026-07-15` e `eod_signals` foi reexecutado.

Resultado pós-correção: `eod_signals` solicitou 150 predições, mas gerou/armazenou 0 sinais. O monitoramento passou a exibir predições recentes com `referenceDate=2026-07-14` e `validFor=2026-07-15`, todas `HOLD` nas 100 linhas exibidas pela API. Portanto, a situação atual deve ser tratada como abstenção do Apolo por confiança direcional insuficiente, não mais como bloqueio de candles.

Próximo passo operacional: acompanhar o pregão de `2026-07-15` sem sinal do Apolo; antes da próxima rodada, verificar se o arquivo oficial da B3/carga diária roda normalmente para evitar novo atraso de candles.

## 2026-07-15 — Recuperação automática implementada no código

Foi implementado mecanismo de recuperação para evitar repetição do bloqueio observado: antes de inferir, `neural_eod_predictions` tenta recuperar candles ausentes chamando `get_stock_data`; antes de desistir, `eod_signals` tenta recuperar candles ausentes e também predições neurais ausentes.

Próximo passo operacional:
1. Fazer deploy de `neural_eod_predictions` e `eod_signals` com as novas variáveis de ambiente padrão, mantendo `ENABLE_DAILY_CANDLES_RECOVERY=true`.
2. Em uma próxima falha de B3/candle, confirmar nos logs se apareceu a chamada automática de recuperação antes do retorno `empty`.
3. Se a operação preferir defesa em profundidade, criar por conta autorizada um Scheduler separado de retry de `get_stock_data` antes de `neural_eod_predictions`; a tentativa via MCP falhou por falta de permissão `cloudscheduler.jobs.create`.
4. Manter a regra: se a recuperação ainda não encontrar candles da `reference_date`, a função não deve inferir com dado defasado; deve retornar vazio e registrar a falha de dados.

## 2026-07-15 — Frequência da evolução do Apolo

Estado confirmado: a trilha do Apolo não está em agendamento horário. O job ativo `neural-evolution-daily` roda uma vez por dia útil operacional (`30 2 * * 2-6`) com `max_trials=1`, por isso somente uma rede/challenger foi analisado em `2026-07-15`.

O job `neural-evolution-phase3-30m` roda a cada 30 minutos, mas é outra estratégia (`phase3_new_families`) e aparece com `status.code=13`; ele não é a Trilha B do Apolo nem o refinamento novo.

Próximo passo se quisermos evolução hora em hora: criar ou alterar Scheduler com cron horário, payload `strategy=apolo_challenger_refinement`, orçamento baixo (`max_trials=1` ou `2`) e sem promoção automática. Essa ação precisa de conta com permissão de Cloud Scheduler, pois a tentativa via MCP falhou por `cloudscheduler.jobs.create`.

## 2026-07-15 — Scheduler horário criado; validar primeira execução real

Estado confirmado: o Scheduler `neural-evolution-apolo-refinement-hourly` existe, está `ENABLED`, roda em `0 * * * *` no timezone `America/Sao_Paulo` e chama `neural_evolution_orchestrator` com payload `strategy=apolo_challenger_refinement`, `max_trials=1` e `train_candidates=true`.

Também foi validado por `dry_run` produtivo que o deploy reconhece a estratégia e gera 1 candidata em modo seco. Porém, nas últimas 6 horas ainda não há run/candidate/gate persistidos no BigQuery para uma execução real do Scheduler horário.

Próximo passo operacional:
1. Aguardar a próxima virada de hora ou executar manualmente `gcloud scheduler jobs run neural-evolution-apolo-refinement-hourly --project=ingestaokraken --location=us-east1`.
2. Depois da tentativa, verificar `neural_evolution_runs`, `neural_candidate_configs` e `neural_gate_decisions` para confirmar gravação de nova candidata.
3. Separadamente, investigar o job antigo `neural-evolution-phase3-30m`, que continua falhando com `No neural evolution candidates were generated` e não deve ser confundido com o refinamento do Apolo.

## 2026-07-15 — Primeira execução real do refinamento concluída

Estado confirmado: o Scheduler `neural-evolution-apolo-refinement-hourly` executou às `2026-07-15T18:00:00Z` e a run `neural_evolution_20260715_180004_6a223366` foi concluída com `strategy=apolo_challenger_refinement`, gerando, treinando e avaliando 1 candidata.

Resultado do Gate: a família `neural_eod_apolo_refine_tabular_bt_p50_m08_t35_dd16_block5` foi rejeitada com `passed=false` por `trades_insuficientes` e `seeds_instaveis`. Isso confirma que o fluxo horário está operacional, mas ainda não há nova rede aprovada além da Apolo.

Próximo passo operacional:
1. Manter o Scheduler horário de refinamento ativo e acompanhar as próximas execuções em `neural_evolution_runs`, `neural_candidate_configs` e `neural_gate_decisions`.
2. Não promover nenhuma candidata até aparecer `passed=true` com estabilidade de seeds/folds e drawdown aceitável.
3. Investigar separadamente o job antigo `neural-evolution-phase3-30m`, que continua produzindo erro `No neural evolution candidates were generated` no mesmo endpoint e pode confundir a leitura dos logs.

## 2026-07-15 — Phase3 antigo não está gerando redes

Estado confirmado: o job `neural-evolution-phase3-30m` está ativo e executa a cada 30 minutos, mas não está gerando redes. Nas últimas 24 horas não há runs/configs/gates de `strategy=phase3_new_families` no BigQuery, e os logs mostram `No neural evolution candidates were generated` a cada tentativa.

Interpretação: os POST 200 vistos nos minutos cheios pertencem ao refinamento horário do Apolo (`apolo_challenger_refinement`), não ao `phase3_new_families`. O phase3 antigo continua falhando com HTTP 500.

Próximo passo operacional:
1. Prioridade: manter o `neural-evolution-apolo-refinement-hourly`, que está gerando e avaliando candidatas.
2. Para o `neural-evolution-phase3-30m`, escolher entre corrigir o espaço de busca/payload da estratégia `phase3_new_families` ou desabilitar o Scheduler para reduzir ruído de erro.
3. Se a intenção for manter exploração broad-phase, executar primeiro um `dry_run` corrigido até retornar `candidate_count>0`; só depois reabilitar/continuar o Scheduler de 30 minutos.

## 2026-07-15 — Correção preparada para o phase3 de 30 minutos

Foi preparada correção no `neural_evolution_orchestrator` para o caso em que `phase3_new_families` não gera candidatas por esgotamento do conjunto deduplicado com seed fixa. Agora, se a primeira geração voltar vazia, somente essa estratégia tenta uma segunda geração com seed fallback estável derivada do `evolution_run_id` e prefixo `reseed`.

Próximo passo operacional após deploy:
1. Fazer deploy do `neural_evolution_orchestrator` corrigido.
2. Executar um `dry_run` produtivo com o payload atual do `neural-evolution-phase3-30m` e confirmar `candidate_count>0`.
3. Aguardar ou disparar o Scheduler `neural-evolution-phase3-30m` e confirmar nova linha em `neural_evolution_runs` com `strategy=phase3_new_families`.
4. Se a estratégia voltar a gerar, manter monitoramento separado do refinamento Apolo para não confundir POST 200/500 no mesmo endpoint.

## 2026-07-16 — Idempotência das previsões do Apolo

Foi preparada correção para impedir novas triplicações em `neural_eod_predictions`: a função passa a tratar predições existentes como sucesso idempotente quando `force=false`, e só substitui linhas existentes quando houver execução explícita com `force=true`.

Próximo passo operacional após deploy:
1. Fazer deploy de `neural_eod_predictions`, `eod_signals` e backend com a deduplicação de monitoramento.
2. Reabrir o painel do champion e confirmar que cada ticker aparece uma vez para `reference_date=2026-07-15`/`valid_for=2026-07-16`.
3. Manter o Scheduler normal; novas coletas/predições automáticas devem ocorrer apenas quando as predições estiverem ausentes ou quando houver `force=true` operacional.
4. Opcionalmente limpar duplicatas históricas em BigQuery com uma rotina controlada, mas a visualização e o consumo operacional já passam a selecionar a linha mais recente por ticker/modelo.

## 2026-07-16 — Fluxo de geração ativo, sem nova aprovada

Estado confirmado: o fluxo de geração de redes está ativo. Nas últimas 24 horas houve runs concluídas de `phase3_new_families`, `apolo_challenger_refinement` e `apolo_challenger_shadow`, todas gerando, treinando, avaliando e gravando decisões de gate.

Ainda não existe rede aprovada além da Apolo: o Gate MUEN segue com apenas 1 `passed=true` em 1040 decisões totais. As candidatas recentes têm alguns deltas positivos, mas falham por `seeds_instaveis`, folds positivos insuficientes, trades insuficientes e/ou drawdown excessivo.

Próximo passo operacional:
1. Manter `neural-evolution-apolo-refinement-hourly` e `neural-evolution-phase3-30m` ativos, pois ambos voltaram a produzir evidência.
2. Monitorar principalmente candidatas com delta positivo e drawdown aceitável, mas não promover sem `passed=true`.
3. Se muitas rodadas continuarem falhando por `seeds_instaveis`, ajustar a estratégia de refinamento para priorizar estabilidade de seeds antes de ampliar arquitetura.

## 2026-07-16 — Novo fluxo de estabilidade para candidatas promissoras

Foi criado o fluxo `apolo_challenger_stability`, direcionado às famílias que já apresentaram delta de expectancy positivo (`wide_deep_mlp` e `tabular_bottleneck_mlp`), mas que foram bloqueadas principalmente por instabilidade entre seeds, poucos trades ou drawdown. Ele não promove modelos automaticamente: executa repetições multi-seed somente nessas duas famílias, com menos variação estrutural, limiares direcionais moderados para não reduzir excessivamente a amostra de trades e `max_fold_drawdown_stop=0.15`.

Próximo passo operacional:
1. Fazer deploy do `neural_evolution_orchestrator` com a estratégia nova.
2. Validar com `dry_run` usando `{"strategy":"apolo_challenger_stability","dry_run":true,"budget":{"max_trials":2,"random_seed":20260716}}`.
3. Se o retorno tiver `candidate_count=2`, criar um Scheduler separado (por exemplo, horário) para essa estratégia; manter o refinamento atual e o phase3 ativos enquanto se compara a taxa de `passed=true`.
4. Promover somente se o Gate MUEN retornar `passed=true`; delta positivo isolado continua insuficiente.
## 2026-07-17 — Estado atual: processo ativo; nenhuma nova aprovada

O processo de criação, validação e melhoria está ativo em produção: nas últimas 24 horas foram concluídas 48 runs de `phase3_new_families`, 24 de `apolo_challenger_refinement`, 23 de `apolo_challenger_stability` e 1 de `apolo_challenger_shadow`. As rodadas recentes geraram candidatas, treinaram e registraram as decisões MUEN.

Ainda não há segunda rede aprovada. Das 1.159 decisões MUEN registradas, apenas uma tem `passed=true`: a família do Apolo NEV, que permanece o champion aprovado. As candidatas com delta de expectativa positivo continuam bloqueadas principalmente por instabilidade entre seeds; drawdown excessivo, folds positivos insuficientes e poucos trades também ocorrem em parte das tentativas.

Próximo passo operacional:
1. Manter as três trilhas de criação ativas e observar se as próximas rodadas mantêm `failed_count=0` nas runs.
2. Priorizar o refinamento das famílias `wide_deep_mlp` e `tabular_bottleneck_mlp` para reduzir `seeds_instaveis`, sem relaxar os gates de drawdown, folds e trades.
3. Só considerar uma nova aprovação quando uma candidata aparecer em `neural_gate_decisions` com `passed=true`; em seguida, comparar com o Apolo e exigir aprovação manual para qualquer promoção.

## 2026-07-17 — Acompanhamento visual da criação neural disponível

A nova tela **Redes neurais > Criação de redes** passa a mostrar diariamente as execuções por estratégia e os totais de candidatas, treinos, decisões de gate e falhas, a partir de `neural_evolution_runs`.

Próximo passo operacional: usar o gráfico para acompanhar continuidade das estratégias e investigar qualquer barra/falha fora do padrão; manter como critério de promoção exclusivamente um novo `passed=true` no Gate MUEN e a aprovação manual.
