# Próximo passo operacional das redes neurais — 2026-07-08 15:15 UTC

Corrigido o erro de CI `F811` reportado em `tests/test_neural_training.py` renomeando o teste de override de `candidate_family_hash` para um nome mais específico e não colidente. O próximo passo operacional das redes permanece: após deploy do commit com `daily_return_count`/`daily_returns`, reexecutar TCN `p50/m08/t20/d15/l20` com sufixo `_ticker_v3`, validar `daily_return_count > 0` e diagnosticar ticker/data/fold antes de qualquer promoção.

---

# Próximo passo operacional das redes neurais — 2026-07-08 15:10 UTC

Formalizado o processo de evolução neural em passos no runbook `docs/implementacao/processo-evolucao-neural-em-passos.md`. A partir de agora, famílias em descoberta (como TCN/GRU Fase 4) devem seguir ciclo manual controlado: hipótese → rastreabilidade/DDL → dry-run → shadow pequeno multi-seed → Gate MUEN + diagnóstico → decisão de repetir/ajustar/descartar/promover manualmente. Scheduler fica reservado para políticas maduras, não para descoberta.

Próximo passo prático: após deploy do commit com `daily_return_count`/`daily_returns`, reexecutar a TCN `p50/m08/t20/d15/l20` com sufixo novo (`_ticker_v3`), validar `daily_return_count > 0`, consultar `neural_daily_returns` por ticker/data/fold e decidir se a falha `seeds_instaveis` justifica mais seeds ou revisão de features/regime. Sem promoção automática.

---

# Próximo passo operacional das redes neurais — 2026-07-08 14:59 UTC

DDL aplicado e rodada shadow TCN `p50/m08/t20/d15/l20_ticker_v2` executada com três seeds. A família foi `rejected`, mas o resultado melhorou bastante: `totalTrades=116`, `positiveFolds=8`, `median_delta=0.0054544894289544`, `worst_delta=0.0`, `maxDrawdown=0.14369556809024991`; falhou apenas por `seeds_instaveis` (`stableAcrossSeeds=false`). Porém a resposta da função não trouxe `daily_return_count` e a consulta em `neural_daily_returns` retornou 0 linhas para a família, indicando que o DDL foi feito, mas o código com persistência de `daily_returns` ainda não está deployado na função.

Próximo passo: fazer deploy do commit que adiciona `daily_return_count`/`daily_returns` e reexecutar a mesma TCN `p50/m08/t20/d15/l20_ticker_v2` (ou sufixo `_ticker_v3`) para coletar ticker/data/fold. Se o padrão se repetir, priorizar diagnóstico de estabilidade entre seeds; não promover enquanto `stableAcrossSeeds=false`.

---

# Próximo passo operacional das redes neurais — 2026-07-08 06:59 UTC

Implementada a rastreabilidade por `ticker` nas linhas `neural_daily_returns` da economia MUEN: o treinamento passa a incluir `daily_returns` com `ticker` no payload `muen_economics`, e o orquestrador passa a persistir essas linhas na tabela `neural_daily_returns`. Isso desbloqueia o diagnóstico pedido de identificar ticker/data/fold que compõem o `worst_delta` nas próximas rodadas.

Próximo passo após deploy: aplicar no BigQuery `ALTER TABLE ingestaokraken.cotacao_intraday.neural_daily_returns ADD COLUMN IF NOT EXISTS ticker STRING` (já versionado em `infra/bq/21_neural_evolution.sql`) e só então reexecutar uma rodada shadow pequena da TCN `p50/m08/t20/d15/l20` para coletar daily returns com ticker. Não promover e não criar Scheduler dedicado; usar a nova rastreabilidade para diagnosticar labels/features/regime por ticker/data/fold.

---

# Próximo passo operacional das redes neurais — 2026-07-08 06:16 UTC

Executado o diagnóstico pós-GRU e a comparação shadow TCN/Conv1D causal `p50/m08/t20/d15/l20` com três seeds. A TCN terminou sem falha técnica e melhorou cobertura/consistência operacional frente à GRU (`totalTrades=132`, `positiveFolds=6`, `positiveFoldRatio=0.5`), mas ainda foi `rejected` pelo Gate MUEN por `nao_supera_champion_mediana`, `fold_catastrofico` e `seeds_instaveis` (`median_delta=-0.01073690133513924`, `worst_delta=-0.07000000000000008`, `stableAcrossSeeds=false`).

Próximo passo: interromper novas rodadas de arquitetura/stop na Fase 4 até fazer diagnóstico de dados. Priorizar investigação de labels/features/regime por fold: identificar quais tickers/datas concentram o `worst_delta`, comparar distribuição de retornos sequenciais entre validation/test e treinar somente depois uma nova política com filtro de regime ou features temporais adicionais. Sem promoção automática e sem Scheduler dedicado.

---

# Próximo passo operacional das redes neurais — 2026-07-08 00:50 UTC

Executadas em shadow as variantes GRU Fase 4 `p50/m08/t20/d15/l20` e `p50/m08/t20/d18/l20`, ambas com três seeds e Gate MUEN agregado. As duas rodadas concluíram sem falhas técnicas, mas foram `rejected`. O stop intrafold cumpriu o objetivo de reduzir drawdown para perto/abaixo de 20% (`d15 maxDrawdown=0.19564300000000054`; `d18 maxDrawdown=0.1995843493000002`), porém não resolveu edge nem estabilidade (`median_delta` negativo e `stableAcrossSeeds=false` nas duas).

Próximo passo: não promover, não criar Scheduler específico e não continuar apertando stop/cap na GRU l20. Priorizar diagnóstico de edge/labels/features sequenciais: decompor os folds/seed com maior perda, revisar se as janelas sequenciais estão capturando regime útil, comparar contra TCN/Conv1D causal com o mesmo `t20/d15/l20` somente após esse diagnóstico, e manter Gate MUEN inalterado.

---

# Próximo passo operacional das redes neurais — 2026-07-08 00:10 UTC

Corrigido o erro de CI `F811` reportado em `tests/test_neural_evolution.py` ao tornar explícitos e únicos os nomes dos testes de repetição multi-seed da Fase 3 e de payload sequencial da Fase 4. Após essa correção, o próximo passo operacional volta a ser o deploy e a execução shadow da GRU Fase 4 `p50/m08/t20/d15/l20` com três seeds, sem promoção automática.

---

# Próximo passo operacional das redes neurais — 2026-07-07 23:00 UTC

Implementado no código o controle de risco intrafold `max_fold_drawdown_stop`, que neutraliza as decisões restantes de um fold depois que o drawdown acumulado atinge o limite configurado. O Gate MUEN permanece inalterado; o controle atua antes da economia MUEN, no pós-processamento da política de decisão.

Próximo passo após deploy: rodar em shadow a GRU Fase 4 `p50/m08/t20/d15/l20` com três seeds, usando `max_trades_per_fold=20`, `max_fold_drawdown_stop=0.15`, `sequence_lookback=20` e `candidate_family_hash=neural_eod_phase4_gru_sequence_p50_m08_t20_d15_l20`. Critério de sucesso: `maxDrawdown < 0.20`, ausência de `fold_catastrofico`, `stableAcrossSeeds=true`, trades suficientes e aprovação MUEN agregada; sem promoção automática mesmo se passar.

---

# Próximo passo operacional das redes neurais — 2026-07-07 22:45 UTC

Recomendação: não testar `t25` agora. O problema da GRU Fase 4 `p50/m08/t20/l20` não foi falta de trades (`totalTrades=204`), e sim risco/estabilidade (`maxDrawdown=0.32213004093848546`, `stableAcrossSeeds=false`). O próximo passo deve ser implementar um controle explícito de risco intrafold antes da economia MUEN, como `max_fold_drawdown_stop` ou neutralização após perda acumulada por fold, sem alterar o Gate MUEN.

Primeiro experimento após essa implementação: repetir a GRU `p50/m08/t20/l20` com três seeds e stop intrafold de 15% a 18%. Critério de sucesso: `maxDrawdown < 0.20`, sem `fold_catastrofico`, `stableAcrossSeeds=true` e trades suficientes. Se isso destruir trades/expectancy, parar de apertar caps e priorizar revisão de features/labels sequenciais.

---

# Próximo passo operacional das redes neurais — 2026-07-07 22:25 UTC

A variação conservadora GRU Fase 4 `p50/m08/t20/l20` foi executada com três seeds e decisão MUEN agregada. Resultado: `rejected`, `seeds=3`, `totalTrades=204`, `positiveFolds=8`, mediana de delta `0.0013468753473707333`, `maxDrawdown=0.32213004093848546` e `stableAcrossSeeds=false`, falhando por `drawdown_excessivo` e `seeds_instaveis`.

Não testar `t25` agora: o critério para isso era `trades_insuficientes`, e o t20 teve 204 trades. Próximo passo: congelar promoção/Scheduler da GRU l20 e só continuar Fase 4 se for para implementar/testar controle explícito de risco temporal, como limitador de drawdown intrafold ou neutralização após perda acumulada, mantendo três seeds e Gate MUEN inalterado.

---

# Próximo passo operacional das redes neurais — 2026-07-07 18:45 UTC

Após o deploy do ajuste Fase 4, executar uma rodada conservadora da GRU recorrente `l20`: `strategy=phase4_recurrent_shadow`, apenas `gru_sequence`, `sequence_lookback=20`, `min_directional_probability=0.50`, `min_directional_margin=0.08`, três seeds e `max_trades_per_fold=20`. Usar `candidate_family_hash=neural_eod_phase4_gru_sequence_p50_m08_t20_l20` e prefixo dedicado para evitar colisão de `model_version`.

Objetivo: atacar os dois critérios que reprovaram o multi-seed anterior (`drawdown_excessivo` e `fold_catastrofico`) sem afrouxar o Gate MUEN. Só testar `max_trades_per_fold=25` se `t20` ficar com `trades_insuficientes`; não criar Scheduler e não executar `approve_if_passed` automático.

---

# Próximo passo operacional das redes neurais — 2026-07-07 18:30 UTC

O diagnóstico multi-seed da GRU Fase 4 `p50/m08/t35/l20` foi executado com sucesso e gerou uma decisão MUEN agregada por família: `seeds=3`, `stableAcrossSeeds=true`, `totalTrades=214`, `positiveFolds=6`, mediana de delta `0.0015811857719783577`, mas `maxDrawdown=0.34890754992364853`; decisão `rejected` por `fold_catastrofico` e `drawdown_excessivo`.

Próximo passo: não promover e não criar Scheduler. Publicar o ajuste local que corrige o rótulo de candidatas Fase 4 para `phase4_recurrent_shadow`; depois testar uma variação conservadora da GRU l20 para reduzir drawdown, começando por `max_trades_per_fold=20` ou `25`, mantendo `p50/m08`, três seeds e Gate MUEN inalterado.

---

# Próximo passo operacional das redes neurais — 2026-07-07 16:15 UTC

A Fase 4 recorrente em shadow foi iniciada. O dry-run `l40` passou, mas a rodada real `l40` falhou porque o snapshot atual tem no máximo 39 linhas de treino por ticker; `sequence_lookback=40` não cria janelas de treino. A rodada `l20` foi executada com sucesso: `trained_count=3`, `failed_count=0`, `fold_metric_count=12`, `family_evaluation_count=3` e `gate_decision_count=3`.

Resultado inicial: GRU/TCN/LSTM `p50_m08_t35_l20` foram treinadas e rejeitadas pelo Gate MUEN. A GRU foi a melhor candidata inicial (`maxDrawdown=0.1826037529105603`, `totalTrades=50`, `positiveFolds=2`, mediana de delta `0.011173039169204084`), mas ainda falhou por folds positivos insuficientes e seed única. Próximo passo: publicar o default Fase 4 ajustado para `sequence_lookback=20` e, se repetir Fase 4, começar por diagnóstico multi-seed controlado da GRU `p50/m08/t35/l20`; não criar Scheduler e não executar `approve_if_passed` automático.

---

# Próximo passo operacional das redes neurais — 2026-07-07 17:05 UTC

Depois do deploy, iniciar a Fase 4 recorrente em shadow com uma sequência manual: primeiro executar o dry-run de `strategy=phase4_recurrent_shadow` com `budget.max_trials=3`; se retornar `gru_sequence`, `lstm_sequence` e `tcn_sequence` com sufixo `p50_m08_t35_l20`, executar uma rodada real pequena; depois validar `/api/ops/neural/training-runs` e `/api/ops/neural/gate-decisions`. Só criar Scheduler separado após essa validação. Não usar `approve_if_passed` automático.

O passo a passo com comandos `curl` e Scheduler opcional está documentado em `docs/neural_evolution_orchestrator_scheduler.md`, seção “Fase 4 recorrente em shadow — início manual pós-deploy”.

---

# Próximo passo operacional das redes neurais — 2026-07-07 16:35 UTC

A Fase 4 recorrente em shadow foi implementada no código. O treino agora consegue materializar janelas point-in-time por ticker com `sequence_lookback` de 20 a 60 pregões e testar `gru_sequence`, `lstm_sequence` e `tcn_sequence`/Conv1D causal, mantendo a avaliação pelo mesmo Gate MUEN e sem promoção automática.

Próximo passo operacional: publicar `functions/neural_training` e `functions/neural_evolution_orchestrator`; executar primeiro um dry-run com `strategy=phase4_recurrent_shadow`, `dry_run=true` e `budget.max_trials=3`; validar que as candidatas geradas são GRU/LSTM/TCN com sufixo `p50_m08_t35_l20` e `sequence_lookback=20`; só então executar uma rodada real pequena em shadow. Não usar `approve_if_passed` automático.

---

# Próximo passo operacional das redes neurais — 2026-07-07 15:55 UTC

O pipeline atual ainda não usa redes recorrentes; ele treina arquiteturas tabulares feed-forward (`mlp`, `residual_mlp`, `wide_deep_mlp` e `tabular_bottleneck_mlp`) sobre linhas EOD independentes. Redes recorrentes fazem sentido como próxima frente de pesquisa, mas exigem antes um dataset sequencial point-in-time com janelas por ativo.

Próximo passo operacional: manter a execução imediata do foco multi-seed `tabular_bottleneck_mlp p50/m08/t35` já implementado. Em paralelo ou logo depois, planejar uma Fase 4 recorrente em shadow: materializar janelas de 20 a 60 pregões por ticker, implementar uma família GRU/LSTM pequena ou TCN/1D causal, registrar `architecture_type` novo e avaliar pelo mesmo Gate MUEN sem promoção automática.

---

# Próximo passo operacional das redes neurais — 2026-07-07 15:25 UTC

O código agora tem um caminho dedicado para avaliação/agregação multi-seed da família/política `tabular_bottleneck_mlp p50/m08/t35`: usar `strategy=phase3_multiseed_focus` no `neural_evolution_orchestrator`.

Próximo passo operacional: publicar `functions/neural_training` e `functions/neural_evolution_orchestrator`; em seguida executar primeiro um dry-run com `strategy=phase3_multiseed_focus` e `budget.max_trials=3`, confirmando que as três candidatas são `tabular_bottleneck_mlp`, têm sufixo `p50_m08_t35` e compartilham o mesmo `candidate_family_hash`. Depois, executar a rodada real controlada com as três seeds e verificar se a decisão MUEN consolidada passa a registrar `seeds=3` e `stable_across_seeds` calculado por família/política. Não promover automaticamente e não afrouxar o Gate MUEN.

---

# Próximo passo operacional das redes neurais — 2026-07-07 14:45 UTC

A análise atual via MCP/BigQuery confirma 721 decisões do Gate MUEN, todas rejeitadas, e 784 modelos no registry ainda como `candidate`. O bloqueio dominante é estabilidade/robustez: `seeds_instaveis` aparece em todas as decisões, enquanto `drawdown_excessivo` ainda aparece na maioria.

Melhor candidato econômico confirmado até agora: `neural_eod_phase3_20260707_tabular_bottleneck_mlp_p50_m08_t35_01`, com `positive_folds=4`, `max_drawdown=0.17061813187037642`, `total_trades=90` e `median_delta_expectancy_vs_champion=0.019152524481104147`, mas rejeitado por `seeds_instaveis`.

Próximo passo operacional: não promover nenhuma rede e não afrouxar o Gate MUEN. Priorizar avaliação/agregação multi-seed controlada da família/política `tabular_bottleneck_mlp p50/m08/t35` e validar/corrigir a consolidação por família/política para que as decisões tenham `seeds > 1` e possam medir `stable_across_seeds` de forma real. Como comparação secundária, monitorar o ponto recorrente `neural_eod_mlp_evo2_20260707_diversity_01` apenas quando ficar simultaneamente abaixo de 20% de drawdown e com 4 folds positivos.

---

# Próximo passo — Redes neurais MUEN

**Última atualização:** 2026-07-04 02:45 UTC
**Última atualização:** 2026-07-04 00:45 UTC
**Protocolo:** `neural_eod_protocol_v1`
**Status:** diversidade controlada Fase 2 e Fase 3 implementada; deploy/validação pendente

## Próximo passo atual

A aba `Redes neurais — Treinos` agora separa o gráfico diário em `Criadas Fase 2`, `Criadas Fase 3` e `Testadas`, evitando a leitura equivocada de que a linha azul sumiu quando o volume de decisões MUEN é muito maior. O próximo passo imediato é publicar o frontend atualizado na VPS e validar visualmente se as séries azul, roxa e verde aparecem no card dos últimos 14 dias com os totais coerentes.

A Fase 3 também recebeu diversidade controlada: depois das configurações base das famílias `residual_mlp`, `wide_deep_mlp` e `tabular_bottleneck_mlp`, novas rodadas passam a variar learning rate, dropout, batch size, epochs e class weight em grade compacta antes de repetir apenas seed. O próximo passo de validação após o deploy é executar dry-run/rodada pequena de `strategy=phase3_new_families` e confirmar que as candidatas com sufixo `_seed` trazem hiperparâmetros variados, mantendo `max_trials=1` para controlar custo.

A evolução neural agora tem fallback de `controlled_diversity` na Fase 2: depois de mutações e variantes simples de arquitetura, o orquestrador tenta novas combinações controladas de topologia MLP e hiperparâmetros antes de repetir apenas a seed. O próximo passo imediato é publicar `functions/neural_evolution_orchestrator`, disparar um dry-run/execução pequena com `phase2.controlled_diversity=true`, `include_seed_repeats=false` e `max_trials=1`, e confirmar que as próximas candidatas trazem `candidate_source=controlled_diversity` quando os grids anteriores estiverem esgotados.

A aba `Redes neurais — Treinos` recebeu também o card `Redes reprovadas por problema ao longo dos dias`, com barras empilhadas dos últimos 14 dias para os critérios do Top 5 de rejeição MUEN. A leitura operacional atual é: o volume recente já é suficiente para diagnosticar gargalos, mas o aumento recomendado não é apenas mais cadência; é aumentar diversidade controlada de famílias/arquiteturas/hiperparâmetros e só ampliar `max_trials`/cadência depois de validar custo, tempo de execução e ausência de fila.

A aba `Redes neurais — Treinos` recebeu um card `Top 5 problemas que reprovam no Gate MUEN`, mostrando os critérios de rejeição mais frequentes nas decisões carregadas, com quantidade, percentual, barra visual e explicação operacional. O próximo passo imediato é publicar o frontend atualizado na VPS e validar visualmente se o ranking aparece acima da tabela `Últimas análises do Gate MUEN`.

A verificação operacional mais recente da tabela `Últimas análises do Gate MUEN` mostrou que as decisões recentes estão concentradas na família/candidata `neural_eod_mlp_evo2_20260702_seed_fresh_01`. Isso é coerente com o fluxo recorrente de Fase 2/MLP testando uma hipótese por execução com seed fresca; a tabela de últimas análises é um recorte temporal de auditoria, não uma prova de que só exista uma família no projeto. O próximo passo operacional permanece publicar/validar as melhorias visuais pendentes e acompanhar se as próximas execuções continuam trazendo diversidade suficiente de famílias/seeds.

A aba `Redes neurais — Treinos` recebeu um card visual adicional com gráfico de linha diário para comparar redes criadas no registry e redes testadas pelo Gate MUEN nos últimos 14 dias. O próximo passo imediato é publicar o frontend atualizado na VPS e validar visualmente que o card aparece abaixo das totalizações, com as linhas “Criadas” e “Testadas” coerentes com as execuções recentes.

As redes da Fase 3 estão incluídas no endpoint/tabela de Treinos. A validação mais recente do endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-runs` mostrou 100 treinos visíveis, dos quais 13 são Fase 3 pelo prefixo `neural_eod_phase3_` e pelas famílias `residual_mlp`, `wide_deep_mlp` e `tabular_bottleneck_mlp`, todas ainda como `candidate`.

O próximo passo imediato é publicar o frontend atualizado na VPS para que a aba `Redes neurais — Treinos` destaque explicitamente a Fase 3 com o cartão “Fase 3 visíveis” e a coluna “Fase/família”. Depois da publicação, confirmar visualmente a contagem na tela e seguir monitorando a cadência de geração, as decisões MUEN e eventuais HTTP 500.


## Experimento v3 em execução — 2026-07-04 00:45 UTC

A recomendação de testar outro conjunto de variáveis foi executada no código: o contrato padrão passou para `feature_eod_tabular_v3`, com 30 features de treino. O v3 adiciona retornos/log-retornos, volatilidades de curto/longo prazo, downside volatility, razões de volume/liquidez, inclinação de médias, distâncias de máximas/mínimas de 60 dias e volatilidade do range diário. O Gate MUEN permanece inalterado.

Próximo passo operacional imediato:

1. Aplicar `infra/bq/17_neural_eod_training_dataset.sql` no BigQuery para adicionar as colunas v3.
2. Redeployar `functions/neural_training_dataset`, `functions/neural_training` e `functions/neural_evolution_orchestrator`.
3. Materializar um novo snapshot com `feature_eod_tabular_v3`/`label_eod_barrier_v2`.
4. Rodar uma comparação controlada v2 versus v3 em walk-forward, mantendo o Gate MUEN inalterado.
5. Repetir somente as melhores famílias v3 com 3 a 5 seeds antes de esperar aprovação, porque avaliações com `seeds=1` continuam sujeitas ao bloqueio `seeds_instaveis`.
6. Só considerar novo `label_version` se a comparação v3 ainda mantiver drawdown incompatível com o limite econômico.


## Verificação BigQuery — 2026-07-04 02:30 UTC

O schema produtivo de `ingestaokraken.cotacao_intraday.neural_eod_training_dataset` já está pronto para o v3: as 11 colunas novas de `feature_eod_tabular_v3` existem como `FLOAT64` nullable. Porém, a materialização ainda não aconteceu: a tabela contém apenas linhas `feature_eod_tabular_v1` e `feature_eod_tabular_v2`, e `neural_dataset_manifests` ainda contém somente manifestos v2.

Próximo passo agora: redeployar `functions/neural_training_dataset`, `functions/neural_training` e `functions/neural_evolution_orchestrator`; em seguida executar `neural_training_dataset` para criar o primeiro snapshot `feature_eod_tabular_v3` e validar que a tabela e o manifesto passam a mostrar v3 antes de iniciar comparação walk-forward v2 versus v3.


## Rechecagem BigQuery — 2026-07-04 02:45 UTC

Nova verificação confirmou o mesmo estado: schema v3 pronto, mas ainda sem materialização. `neural_eod_training_dataset` continua sem linhas `feature_eod_tabular_v3`; `neural_dataset_manifests` continua somente com manifestos v2; e `neural_training_dataset` não apresentou logs nas últimas 6 horas.

Próxima ação objetiva: publicar/confirmar o deploy de `functions/neural_training_dataset` com o código v3 e executar a função para gerar um snapshot novo. A validação de sucesso será observar `feature_eod_tabular_v3` na agregação por `feature_version` e um manifesto v3 correspondente em `neural_dataset_manifests`.

## Primeiro passo recomendado — 2026-07-04 03:20 UTC

Antes de mexer em treino, aprovação ou parâmetros do Gate MUEN, faça primeiro uma única ação: **publicar/confirmar o deploy de `functions/neural_training_dataset` com o código que gera `feature_eod_tabular_v3` e executar essa função para materializar o primeiro snapshot v3**. Sem esse snapshot, qualquer treino novo continuará usando o dataset v2 mais recente e não testará as novas variáveis de entrada.

Critério objetivo para considerar o primeiro passo concluído: a consulta por `feature_version` em `ingestaokraken.cotacao_intraday.neural_eod_training_dataset` deve mostrar linhas `feature_eod_tabular_v3`, e `neural_dataset_manifests` deve ter um manifesto v3 correspondente. Só depois disso vale redeployar/rodar `neural_training` e `neural_evolution_orchestrator` para comparar v2 versus v3.


## Verificação MCP — 2026-07-04 23:00 UTC

O MCP Server respondeu ao `initialize` por HTTP e a chamada `cloud_run_function_logs` para `neural_training_dataset` retornou `row_count=0` nas últimas 12 horas. As consultas `bigquery_query` pelo MCP não conseguiram validar as tabelas porque o próprio MCP retornou erro de credencial do `gcloud` (`Credentials` sem `private_key_id`). Como evidência complementar, o endpoint publicado de treinos ainda mostra as execuções mais recentes com `feature_eod_tabular_v2`, 19 features e snapshot `neural_eod_training_dataset_2026-06-27_313c9df2`. Portanto, o primeiro passo ainda deve ser tratado como pendente até uma consulta BigQuery bem-sucedida mostrar linhas/manifesto `feature_eod_tabular_v3`.



## Diagnóstico operacional — 2026-07-06 13:25 UTC

O painel mostra uma falha sistêmica, não um erro pontual de UI: as 680 decisões MUEN carregadas estão rejeitadas. Os bloqueios dominantes são `drawdown_excessivo` e `seeds_instaveis` em 100% das rejeições, seguidos de `folds_positivos_insuficientes` em 566/680 e `nao_supera_champion_mediana` em 104/680.

O próximo passo operacional muda para uma correção em duas frentes antes de aumentar cadência ou promover qualquer modelo:

1. **Dados:** materializar e validar o primeiro snapshot `feature_eod_tabular_v3`, pois os treinos publicados continuam majoritariamente em `feature_eod_tabular_v2` com 19 features.
2. **Risco/estabilidade:** rodar uma rodada pequena com política de decisão conservadora: limiar mínimo de confiança/margem para BUY/SELL, mais classe `neutral`, limite de exposição/trades por fold, stop/volatility targeting no avaliador econômico e repetição de finalistas por 3 a 5 seeds da mesma família.

Não afrouxar `max_drawdown` nem `require_stable_seeds` do Gate MUEN. Se uma candidata tem expectancy mediana positiva mas drawdown de 45% a 90% e `seeds=1`, ela deve continuar reprovada.



## Implementação aplicada — 2026-07-06 14:05 UTC

Foi implementada a primeira melhoria técnica para atacar as reprovações sem afrouxar o Gate MUEN: o treino neural agora usa uma política econômica conservadora antes de calcular as métricas MUEN. BUY/SELL só são considerados quando a melhor classe direcional supera `min_directional_probability=0.45` e também fica pelo menos `min_directional_margin=0.05` acima da classe `neutral`; previsões fracas viram `neutral`.

Ação que precisa ser feita fora do código local: **redeployar `functions/neural_training` e `functions/neural_evolution_orchestrator`**. Depois do deploy, rodar uma execução pequena e validar em `neural_model_registry.hyperparameters_json` que as novas candidatas trazem `min_directional_probability` e `min_directional_margin`.

Se o painel continuar mostrando `drawdown_excessivo` em massa, o próximo ajuste recomendado é subir os limiares no payload para `min_directional_probability=0.50` e `min_directional_margin=0.08`; se ainda não resolver, testar `0.55` e `0.10`. Não alterar o limite do Gate MUEN.



## Validação pós-deploy — 2026-07-06 18:20 UTC

Depois do deploy informado, o dry-run produtivo de `neural_evolution_orchestrator` com `strategy=phase3_new_families`, `dry_run=true` e `max_trials=1` funcionou: retornou HTTP 200 e gerou uma candidata `phase3_family`.

A rodada pequena treinada ainda falhou porque `neural_training` validou o dataset como `feature_eod_tabular_v3`, mas o orquestrador selecionou o snapshot `neural_eod_training_dataset_2026-06-27_313c9df2`, que ainda é `feature_eod_tabular_v2`. A causa foi confirmada nos logs via MCP: `ValueError: feature_version must be feature_eod_tabular_v3`.

Correção local aplicada: o orquestrador agora injeta `feature_version`/`label_version` reais do snapshot no payload de treino, e `neural_training` aceita esses campos. Também foi corrigido `train_candidates=false` para persistir configurações sem tentar avaliar registry inexistente.

Ação necessária agora: **fazer novo deploy de `functions/neural_training` e `functions/neural_evolution_orchestrator` com esta correção**. Depois, repetir a rodada pequena treinada. A materialização do snapshot `feature_eod_tabular_v3` continua sendo o passo estrutural para testar as novas variáveis, mas esta correção desbloqueia o treino com snapshot v2 enquanto o v3 não existe.



## Validação após deploy final informado — 2026-07-06 18:55 UTC

A validação produtiva mostrou avanço parcial: o orquestrador está atualizado. O dry-run Fase 3 retornou HTTP 200; o modo `train_candidates=false` também retornou HTTP 200 com `skipped_count=1`; e o BigQuery confirmou que `training_request_json` já está sendo gravado com `feature_version=feature_eod_tabular_v2`, `label_version=label_eod_barrier_v2`, `min_directional_probability=0.45` e `min_directional_margin=0.05`.

A execução treinada pequena ainda falhou porque `neural_training` continua registrando nos logs `ValueError: feature_version must be feature_eod_tabular_v3`. Como o payload gravado pelo orquestrador já contém `feature_eod_tabular_v2`, a pendência agora está isolada em `functions/neural_training`: a revisão publicada ainda não está usando `feature_version`/`label_version` do payload ou não recebeu o deploy correto dessa alteração.

Ação necessária agora: **redeployar especificamente `functions/neural_training` a partir do commit que altera `_training_config` para usar `payload.get("feature_version")` e `payload.get("label_version")`**. Depois disso, repetir a execução treinada pequena com `strategy=phase3_new_families` e `max_trials=1`.



## Revalidação após novo deploy — 2026-07-06 20:05 UTC

Após o novo deploy, a rodada pequena treinada ainda falhou em `neural_training` com `ValueError: feature_version must be feature_eod_tabular_v3`. O BigQuery confirmou novamente que o orquestrador já envia/grava `feature_version=feature_eod_tabular_v2`; portanto o problema continua isolado no runtime de `neural_training`.

Foi aplicado hardening adicional no código de `functions/neural_training`: depois de carregar o dataset, a função passa a alinhar a configuração ao contrato real do snapshot (`feature_version`/`label_version`) usando os valores únicos do próprio dataset quando o payload não trouxer versões.

Ação necessária agora: **redeployar `functions/neural_training` com este hardening** e repetir a rodada pequena. Se o mesmo erro continuar depois desse deploy, validar o pacote-fonte efetivamente enviado ao Cloud Functions, porque o runtime publicado estará divergindo do código esperado.



## Nova tentativa produtiva — 2026-07-06 21:20 UTC

A nova tentativa após deploy ainda retornou HTTP 500 em `neural_training`, com o mesmo erro `ValueError: feature_version must be feature_eod_tabular_v3`. A consulta ao BigQuery confirmou que o orquestrador continua enviando `feature_version=feature_eod_tabular_v2`, então o ponto de falha restante está dentro do pacote de treino carregado pela função.

Foi aplicado hardening adicional diretamente em `sisacao8/neural_training.train_baseline_mlp`: antes de escolher as colunas por versão e validar o dataset, o helper agora realinha `BaselineMlpConfig.feature_version`/`label_version` aos valores únicos encontrados no próprio dataset carregado.

Ação necessária agora: **redeployar `functions/neural_training` garantindo que a cópia vendorizada `functions/neural_training/sisacao8/neural_training.py` entre no pacote**. Depois disso, repetir primeiro uma chamada direta pequena de `neural_training` ou a rodada pequena do orquestrador.



## Evidência de pacote vendorizado antigo — 2026-07-06 21:35 UTC

Mesmo após o deploy informado, uma chamada direta pequena para `neural_training` com `feature_version=feature_eod_tabular_v2`, `hidden_units=[8]` e `epochs=1` ainda retornou HTTP 500. O stack trace produtivo aponta `train_baseline_mlp` em `/workspace/sisacao8/neural_training.py` linha 234, mas no código atual essa linha local já não corresponde a `train_baseline_mlp`; isso indica que a Cloud Function ainda está executando uma cópia vendorizada antiga de `sisacao8/neural_training.py`.

Ação necessária agora: revisar o workflow/comando de deploy de `neural_training` para garantir que o source enviado é **a pasta completa `functions/neural_training/`**, incluindo `functions/neural_training/sisacao8/neural_training.py`. Depois de corrigir o pacote de deploy, repetir primeiro a chamada direta pequena de `neural_training` antes de acionar o orquestrador.



## Workflow de deploy revisado — 2026-07-06 21:50 UTC

O workflow `.github/workflows/deploy.yml` já apontava `neural_training` para `source: functions/neural_training`, mas não provava no log qual conteúdo vendorizado estava sendo empacotado. Foi adicionada uma validação antes do `gcloud functions deploy`: para `neural_training`, o workflow agora exige que `functions/neural_training/sisacao8/neural_training.py` exista e contenha `align_config_to_dataset`; também imprime fingerprint SHA-256 do source e do arquivo vendorizado, além das linhas 180-260 desse arquivo.

Ação necessária agora: executar novamente o workflow `Deploy`. Se o pacote estiver correto, o log de `neural_training` deve mostrar `align_config_to_dataset` nas linhas impressas e a função receberá `DEPLOY_SOURCE_FINGERPRINT`/`DEPLOY_GITHUB_SHA` como env vars para auditoria. Depois disso, repetir a chamada direta pequena de `neural_training`.



## Causa no validador de dataset — 2026-07-06 23:45 UTC

O deploy com fingerprint mostrou que a cópia vendorizada atualizada já entrou, mas a chamada direta ainda falhou. A causa remanescente está no validador: `train_baseline_mlp` realinhava o `config.feature_version`, porém `_validate_dataset` ainda comparava o dataset contra as constantes globais `FEATURE_VERSION`/`LABEL_VERSION` do código.

Correção aplicada: `prepare_training_arrays` passa a aceitar `expected_feature_version`/`expected_label_version`; `train_baseline_mlp` envia `config.feature_version`/`config.label_version`; e `_validate_dataset` usa esses valores parametrizados.

Ação necessária agora: redeployar `functions/neural_training` mais uma vez e repetir a chamada direta pequena.

## Regra operacional

Não automatizar `approve_if_passed` nem promover modelos para `approved` sem decisão MUEN `passed` e autorização humana explícita. As candidatas Fase 3 devem permanecer em pesquisa/shadow até passarem pelo gate econômico governado.

---

## Histórico anterior


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

## Verificação da tela Treinos — 2026-06-29 13:45 UTC

Verificação inicial limitada ao leaderboard: os 100 itens ordenados por score não mostravam Fase 3. Essa conclusão foi corrigida pela investigação posterior de 13:54 UTC: o BigQuery e o registro de treinos confirmaram três candidatas reais `phase3_family`; o problema atual é esgotamento/deduplicação do espaço inicial da Fase 3.

## Causa real pós-deploy da Fase 3 — 2026-06-29 13:54 UTC

O deploy da Fase 3 funcionou parcialmente: o BigQuery já contém três candidatas reais `phase3_family` (`tabular_bottleneck_mlp`, `residual_mlp` e `wide_deep_mlp`) com prefixo `neural_eod_phase3_`, todas treinadas, avaliadas e rejeitadas pelo Gate MUEN. O problema atual é esgotamento/deduplicação do espaço inicial: após criar uma configuração fixa por família, novas chamadas com `strategy=phase3_new_families` não geravam nenhuma candidata inédita e a função retornava HTTP 500 com `ValueError: No neural evolution candidates were generated`. O código foi ajustado para repetir famílias de Fase 3 com seeds frescas quando as combinações base já existirem. Próximo passo: redeployar `functions/neural_evolution_orchestrator` com essa correção e validar que o dry-run/execução pequena volta a retornar candidatas `phase3_family` em vez de 500.

## Contagem atual da Fase 3 — 2026-06-29 16:10 UTC

A Fase 3 está gerando redes após a correção por seeds frescas. A validação corrigida mostra 7 candidatas Fase 3 no BigQuery/registry: 2 `residual_mlp`, 2 `wide_deep_mlp` e 3 `tabular_bottleneck_mlp`, todas ainda com `status=candidate`. O endpoint publicado de treinos havia mostrado apenas 6 no recorte inicial de 100 linhas, mas o MCP/BigQuery voltou a funcionar após retries e confirmou o total maior. As mais recentes continuam sendo as criadas em sequência às 15:02, 15:31 e 16:01 UTC com sufixos `seed20290633`, `seed20290634` e `seed20290635`.

Próximo passo operacional: continuar monitorando se a cadência de Fase 3 segue criando exatamente uma candidata por execução sem HTTP 500, acompanhar decisões MUEN dessas candidatas e não promover/automatizar `approve_if_passed` sem decisão humana explícita.

## Correção da contagem canônica Fase 3 — 2026-06-29 16:20 UTC

A falha anterior do `bigquery_query` foi reavaliada e se mostrou temporária no runtime remoto do MCP/Cloud SDK: após retries, o MCP voltou a responder consultas via `bq_cli`. A contagem canônica pelo BigQuery em `neural_model_registry` é 7 candidatas Fase 3, todas `candidate`: 2 `residual_mlp`, 2 `wide_deep_mlp` e 3 `tabular_bottleneck_mlp`. O número 6 veio do endpoint de treinos no recorte visível e não incluía a candidata base `tabular_bottleneck_mlp` das 09:01:02 UTC.

Próximo passo operacional permanece monitorar a geração recorrente de Fase 3, decisões MUEN e ausência de HTTP 500, sem promoção automática.
A Fase 3 está gerando redes após a correção por seeds frescas. O endpoint publicado de treinos mostra 6 candidatas Fase 3 no recorte atual: 2 `residual_mlp`, 2 `wide_deep_mlp` e 2 `tabular_bottleneck_mlp`, todas ainda com `status=candidate`. As mais recentes foram criadas em sequência às 15:02, 15:31 e 16:01 UTC com sufixos `seed20290633`, `seed20290634` e `seed20290635`.

Próximo passo operacional: continuar monitorando se a cadência de Fase 3 segue criando exatamente uma candidata por execução sem HTTP 500, acompanhar decisões MUEN dessas candidatas e não promover/automatizar `approve_if_passed` sem decisão humana explícita.

## Próximo passo após diagnóstico do limite do gate — 2026-06-30 08:18 UTC-3

O cartão “Rejeitadas no gate” agora deve ser lido como recorte das últimas decisões carregadas pela API. Como o backend atual limita `/api/ops/neural/gate-decisions` a 50 linhas, o frontend foi ajustado para exibir `50+` quando esse limite for atingido. Próximo passo operacional: se for necessário acompanhar o total histórico real, evoluir o backend para retornar agregados/counts separados da listagem paginada, sem remover o limite da tabela de últimas tentativas.

## Próximo passo após contagem histórica do gate — 2026-06-30 08:31 UTC-3

A tela Treinos passa a depender dos campos agregados `totalDecisions`, `rejectedDecisions` e `passedDecisions` no endpoint `/api/ops/neural/gate-decisions` para mostrar número histórico correto no cartão “Rejeitadas no gate”, mantendo a tabela de auditoria limitada às últimas 50 decisões. Próximo passo operacional: publicar backend e frontend juntos; se apenas o frontend for publicado, ele mantém fallback para o recorte carregado até o backend novo estar em produção.

## Próximo passo após contagem histórica de candidatas — 2026-06-30 10:54 UTC-3

A tela Treinos agora precisa do backend atualizado para mostrar contagens históricas corretas do registry nos cartões “Total de redes”, “Candidatas”, “Em treino agora”, “Aprovadas” e “Rejeitada no registro”. Próximo passo operacional: publicar backend e frontend juntos; após deploy, validar que “Candidata” deixa de refletir o limite visual de 100 linhas e passa a refletir `candidateRuns` vindo de `/api/ops/neural/training-runs`.

## Próximo passo após limpeza visual da aba Treinos — 2026-06-30 13:50 UTC

A aba `Redes neurais — Treinos` foi simplificada removendo os cards superiores redundantes destacados pelo usuário. A alteração é apenas visual/organizacional: permanecem o guia `Como ler o estágio de cada rede`, a auditoria do Gate MUEN e os indicadores de treino/teste. Próximo passo operacional permanece publicar backend e frontend juntos para validar os agregados históricos vindos de `/api/ops/neural/training-runs` e `/api/ops/neural/gate-decisions`, acompanhando a geração recorrente da Fase 3 e decisões MUEN sem promoção automática.

## Próximo passo após remoção de limites remanescentes nos contadores — 2026-06-30 17:18 UTC

A tabela `Últimas análises do Gate MUEN` agora mostra `Data` como primeira coluna. Os contadores `Fase 3` e `Pode ser testada` foram migrados para agregados históricos vindos de `/api/ops/neural/training-runs` (`phase3Runs` e `pendingGateCandidateRuns`), evitando dependência do recorte visual de 100 treinos ou 50 decisões. Próximo passo operacional: publicar backend e frontend juntos e validar na VPS que os cartões refletem os agregados históricos enquanto a tabela continua limitada apenas como listagem de auditoria.

## Próximo passo após correção do erro de Treinos — 2026-06-30 17:31 UTC

A falha HTTP 502 da aba `Redes neurais — Treinos` foi corrigida no código qualificando o alias do registry (`r.model_version` e `r.metrics_json`) na subquery de decisões MUEN. Próximo passo operacional: publicar o backend atualizado, validar `GET http://34.194.252.70/api/ops/neural/training-runs` retornando HTTP 200 e então confirmar na tela que o alerta “Erro ao carregar os treinos neurais” desapareceu. Manter a publicação conjunta do frontend/backend quando houver mudanças visuais pendentes e não automatizar promoção de modelos sem decisão MUEN `passed` e autorização humana explícita.

## Próximo passo após totalizações do dia anterior — 2026-06-30 18:05 UTC

A aba `Redes neurais — Treinos` agora tem um grupo adicional de totalizações limitado ao dia anterior, calculado no frontend a partir de `trainedAt` dos treinos e `decidedAt` das decisões MUEN carregadas. Próximo passo operacional: publicar o frontend atualizado junto com o backend pendente, validar na VPS que o novo grupo aparece abaixo das totalizações gerais e conferir se os valores do dia anterior batem com as execuções/decisões esperadas. Manter a regra de não promover modelos sem decisão MUEN `passed` e autorização humana explícita.

## 2026-07-02 19:20 UTC — Próximo passo após diagnóstico do gráfico diário
O gráfico `Redes criadas x testadas por dia` não estava refletindo todo o histórico recente porque os endpoints publicados truncavam os payloads em 100 treinos e 50 decisões MUEN. A correção no backend amplia ambos os limites para 1000 registros. Próximo passo operacional: publicar o backend atualizado na VPS e validar novamente os endpoints `/api/ops/neural/training-runs` e `/api/ops/neural/gate-decisions`; depois recarregar a tela de treinos para confirmar que os dias 28/06, 29/06, 30/06 e 01/07 deixam de aparecer zerados/incorretos quando há dados no BigQuery.

## Próximo passo após validação produtiva da correção v2/v3 — 2026-07-07 01:10 UTC

O deploy mais recente corrigiu o problema operacional que impedia treinos com o snapshot produtivo v2: uma chamada direta pequena para `neural_training` retornou HTTP 200 e uma rodada real mínima do `neural_evolution_orchestrator` com `strategy=phase3_new_families` treinou, persistiu e avaliou a candidata `neural_eod_phase3_20260707_residual_mlp_01` sem falhas de função.

A candidata nova foi corretamente rejeitada pelo Gate MUEN por `folds_positivos_insuficientes`, `drawdown_excessivo` e `seeds_instaveis`: `maxDrawdown=0.38696099591144445`, `totalTrades=354`, `positiveFolds=2` e `stableAcrossSeeds=false`. Portanto, o problema deixou de ser deploy/compatibilidade de versão e voltou a ser qualidade financeira da política/modelo.

Próximo passo operacional: manter o Gate MUEN inalterado e executar a próxima rodada com política de decisão mais conservadora que o padrão atual, começando por `min_directional_probability=0.50` e `min_directional_margin=0.08`. Se o drawdown continuar acima de 20%, subir para `0.55/0.10`. Só repetir por 3 a 5 seeds as famílias que reduzirem drawdown, mantiverem trades suficientes e melhorarem folds positivos; não promover nenhum modelo sem decisão MUEN `passed` e autorização humana explícita.

## Próximo passo após experimento conservador `0.50/0.08` versus `0.55/0.10` — 2026-07-07 01:20 UTC

Foram executadas duas rodadas reais mínimas da família `residual_mlp` com política de decisão mais conservadora. A rodada `0.50/0.08` (`neural_eod_phase3_20260707_residual_mlp_seed20290708_01`) melhorou a consistência temporal: `positiveFolds=4`, `positiveFoldRatio=1.0` e `medianDeltaExpectancyVsChampion=0.009812008442294535`, mas ainda foi rejeitada por `drawdown_excessivo` e `seeds_instaveis`, com `maxDrawdown=0.32282251255370137` e `totalTrades=420`.

A rodada mais rígida `0.55/0.10` (`neural_eod_phase3_20260707_residual_mlp_seed20290709_01`) piorou: voltou para `positiveFolds=2`, `positiveFoldRatio=0.5`, `maxDrawdown=0.6774098920768425` e `totalTrades=676`. Portanto, o melhor ponto testado nesta etapa é `0.50/0.08`, mas ele ainda não passa no Gate MUEN.

Próximo passo operacional: parar de subir apenas o limiar de probabilidade/margem e implementar controle econômico explícito antes da avaliação MUEN — limite de trades/exposição por fold, volatility targeting ou stop/cap de perda acumulada por fold. O Gate MUEN permanece inalterado. Só repetir `0.50/0.08` em 3 a 5 seeds se uma variação com drawdown abaixo de 20% for obtida.

## Próximo passo após implementar limitador de trades por fold — 2026-07-07 01:45 UTC

Foi implementado o controle econômico explícito `max_trades_per_fold`. Ele atua depois da política conservadora de labels e antes da economia MUEN: mantém somente as operações direcionais de maior convicção por fold e transforma o excedente em `neutral`, reduzindo exposição/turnover sem alterar o Gate MUEN.

Próximo passo operacional: publicar `functions/neural_training` e `functions/neural_evolution_orchestrator`; em seguida executar uma rodada real mínima com a melhor política anterior (`min_directional_probability=0.50`, `min_directional_margin=0.08`) e `max_trades_per_fold=60`. Se `maxDrawdown` continuar acima de 20%, repetir com `max_trades_per_fold=40` e depois `30`. Só considerar repetição multi-seed quando uma combinação ficar abaixo de 20% de drawdown e mantiver folds positivos suficientes.

## Próximo passo após validação do cap 60 e correção de sufixo de política — 2026-07-07 02:55 UTC

A rodada pós-deploy com `max_trades_per_fold=60` treinou e avaliou sem erro, e o cap foi efetivo para reduzir trades (`totalTrades=240`), mas a candidata ainda foi rejeitada pelo Gate MUEN com `maxDrawdown=0.3401409399120135`. A validação também revelou que o gerador Fase 3 não estava propagando `min_directional_probability`/`min_directional_margin` de `phase3.family_space` para os hiperparâmetros e reutilizava `model_version` sem sufixo da política, causando colisão com versões anteriores.

A correção local já foi aplicada: Fase 3 agora propaga `min_directional_probability`, `min_directional_margin` e `max_trades_per_fold` para os hiperparâmetros, e `model_version` passa a incluir sufixos como `_p50_m08_t60` quando a política de trading difere do padrão.

Próximo passo operacional: redeployar `functions/neural_evolution_orchestrator`; depois repetir `residual_mlp` com `min_directional_probability=0.50`, `min_directional_margin=0.08` e `max_trades_per_fold=60`. Se `maxDrawdown` continuar acima de 20%, testar `max_trades_per_fold=40` e `30`. Não repetir seeds nem promover modelos até uma combinação ficar abaixo do limite de drawdown e manter folds positivos suficientes.

## Próximo passo após caps 60/40/30/20/18 — 2026-07-07 03:35 UTC

As rodadas com sufixo de política confirmaram que o versionamento está correto e que `max_trades_per_fold` atua na economia MUEN. Resultado: `t60` e `t40` mantiveram `positiveFolds=4`, mas ainda falharam por drawdown (`0.3030` e `0.2424`); `t18` removeu `drawdown_excessivo` (`maxDrawdown=0.1850`), mas caiu para `positiveFolds=2` e falhou por `folds_positivos_insuficientes`.

Próximo passo operacional: não promover nem repetir seeds dessas candidatas ainda. Implementar um stop/limitador de drawdown intrafold antes da economia MUEN, buscando preservar a cobertura/folds positivos do cap 40 enquanto bloqueia novas operações quando o drawdown acumulado se aproximar de 18%–20%. Depois do deploy desse stop, repetir primeiro `p50/m08/t40` com stop de 18% e comparar contra `t18`.

## Regra de parada — congelar família atual e priorizar v3/features/labels — 2026-07-07 04:05 UTC

Regra oficial: não continuar criando camadas adicionais de contenção para tentar aprovar a família atual quando a evidência mostra falta de edge robusto. A família `residual_mlp` com política `p50/m08` e caps por fold fica congelada para promoção, repetição multi-seed e novas variações incrementais de risco.

Leitura dos resultados: `t40` preservou folds positivos, mas ainda ficou acima do limite de drawdown; `t18` removeu `drawdown_excessivo`, mas perdeu consistência temporal. Isso indica que o problema não é apenas calibragem de risco, e sim insuficiência da hipótese/modelo/dados atuais.

Novo próximo passo operacional: executar no máximo um último diagnóstico simples e, em seguida, priorizar `feature_eod_tabular_v3`, revisão de labels, novas features e segmentação por regimes de mercado. Só voltar a treinar/promover famílias neurais quando houver nova hipótese estrutural de dados ou target; não promover nenhum modelo sem decisão MUEN `passed` e autorização humana explícita.

## Próximo passo após congelar `residual_mlp` e testar outras famílias — 2026-07-07 04:20 UTC

A `residual_mlp p50/m08` fica congelada. O diagnóstico pequeno em outras famílias mostrou que `wide_deep_mlp p50/m08/t40` ainda tem drawdown alto (`0.2811`), enquanto `tabular_bottleneck_mlp` é mais promissora. O melhor ponto foi `tabular_bottleneck_mlp p50/m08/t35`: `positiveFolds=4`, `maxDrawdown=0.1706`, `totalTrades=90` e `medianDeltaExpectancyVsChampion=0.01915`, falhando apenas por `seeds_instaveis`.

Novo próximo passo operacional: não promover ainda. Rodar diagnóstico multi-seed controlado da família `tabular_bottleneck_mlp p50/m08/t35`. Antes de promoção, confirmar que a avaliação consolida seeds por família/política; se o runtime continuar registrando `seed_count=1` por `model_version`, corrigir a agregação multi-seed antes de aprovar qualquer modelo.

## 2026-07-08 18:10 UTC — Próximo passo após TCN ticker_v3 com rastreabilidade ativa
- Após o deploy com persistência de `daily_returns`, executei dry-run e rodada real da TCN Fase 4 `p50/m08/t20/d15/l20_ticker_v3` com três seeds pelo `neural_evolution_orchestrator`.
- A rodada confirmou que a versão publicada já está persistindo a trilha diária: a resposta operacional trouxe `daily_return_count=9900`, com `trained_count=3`, `evaluated_count=3`, `failed_count=0`, `fold_metric_count=12`, `family_evaluation_count=1` e `gate_decision_count=1`.
- O Gate MUEN consolidado rejeitou a família `neural_eod_phase4_tcn_sequence_p50_m08_t20_d15_l20_ticker_v3`: `seeds=3`, `total_trades=68`, `positive_folds=2`, `positive_fold_ratio=0.16666666666666666`, `median_delta=-0.003538582548495635`, `worst_delta=-0.07000000000000006`, `max_drawdown=0.1956430000000005`, `stable_across_seeds=false`.
- Critérios falhos: `folds_positivos_insuficientes`, `nao_supera_champion_mediana`, `fold_catastrofico` e `seeds_instaveis`. Portanto, não há promoção, não há Scheduler dedicado e a TCN ticker_v3 não deve ser repetida como candidata de aprovação.
- A nova rastreabilidade por ticker funcionou e mostrou que as piores perdas estão concentradas em operações em que o champion ficou neutro e o modelo entrou comprado/vendido com perda aproximada de 7%, especialmente em `ONCO3` nas datas 2026-06-08, 2026-06-09, 2026-06-10 e 2026-06-19, além de eventos em `BRKM5` e `CSAN3`.
- Próximo passo operacional: pausar novas arquiteturas/novos stops e implementar diagnóstico/filtro de cauda por ticker/data/regime antes de retreinar. O foco deve ser explicar por que a sequência entra quando o champion está neutro nesses tickers e criar uma guarda operacional, por exemplo filtro de regime/liquidez/evento ou neutralização de tickers/datas com comportamento de cauda, mantendo o Gate MUEN inalterado.
- Comandos usados: Python `urllib.request` com `/tmp/phase4_tcn_d15_ticker_v3_payload.json` para dry-run e execução real; MCP HTTP JSON-RPC em `http://mcpserversisacao.shop/mcp` com `bigquery_query` para validar `neural_gate_decisions` e `neural_daily_returns` por ticker/data/fold.

## 2026-07-08 18:35 UTC — Próximo passo implementado: guarda explícita por ticker de cauda
- Como a TCN ticker_v3 falhou por entradas concentradas em `ONCO3`, `BRKM5` e `CSAN3` quando o champion estava neutro, implementei o próximo passo técnico como uma guarda configurável `blocked_tickers` na política de avaliação MUEN.
- A guarda neutraliza decisões direcionais para tickers explicitamente listados no payload antes do stop intrafold e antes da economia MUEN; ela não altera o Gate MUEN, não promove modelos automaticamente e não aprende a lista dentro da própria rodada.
- A geração de candidatos agora propaga `blocked_tickers` em `training_request`/hiperparâmetros e inclui um sufixo compacto `btN_<hash>` no `model_version`, permitindo comparar uma rodada shadow guardada contra a TCN ticker_v3 sem colisão de versão.
- Próximo passo operacional pós-deploy: executar uma única rodada shadow TCN `p50/m08/t20/d15/l20` com `blocked_tickers=["ONCO3","BRKM5","CSAN3"]` e sufixo novo, validando se a remoção dessas caudas melhora `positive_folds`, `median_delta` e estabilidade sem reduzir trades a nível insuficiente.
- Se a melhora vier apenas por exclusão oportunista e continuar `seeds_instaveis`, não promover; transformar a lista em regra explicável de regime/liquidez/evento antes de qualquer Scheduler.
- Comandos usados: edição de `sisacao8/neural_training.py`, `functions/neural_training/sisacao8/neural_training.py`, `functions/neural_training/main.py`, `sisacao8/neural_evolution.py`, `functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py` e testes associados; `python -m black` nos arquivos alterados.

## 2026-07-08 20:05 UTC — Próximo passo após TCN com `blocked_tickers`
- Executei dry-run e rodada real da TCN Fase 4 `p50/m08/t20/d15/l20` com `blocked_tickers=["ONCO3","BRKM5","CSAN3"]`, três seeds e `candidate_family_hash=neural_eod_phase4_tcn_sequence_p50_m08_t20_d15_l20_bt3_onco3_brkm5_csan3_v1`.
- A rodada confirmou a guarda em produção: os candidatos receberam sufixo `bt3_407e4c`, a execução retornou HTTP 200, `trained_count=3`, `evaluated_count=3`, `failed_count=0`, `daily_return_count=9900`, `fold_metric_count=12`, `family_evaluation_count=1` e `gate_decision_count=1`.
- Resultado MUEN: `decision_status=rejected`, mas houve melhora relevante contra a TCN ticker_v3: `stable_across_seeds=true`, `median_delta=0.007912287316774284`, `positive_folds=6`, `positive_fold_ratio=0.5`, `total_trades=52`, `max_drawdown=0.19564300000000023`; falhou somente por `fold_catastrofico`, com `worst_delta=-0.03500000000000004`.
- A consulta por `neural_daily_returns` mostrou que as novas piores caudas migraram para `ARML3` em 2026-06-24/2026-06-25 e `RCSL3` em 2026-06-10/2026-06-18, novamente em operações nas quais o champion ficou neutro e o modelo assumiu exposição.
- Próximo passo operacional: não promover e não ampliar blocklist manualmente ticker a ticker. O resultado provou que a guarda reduz instabilidade, mas também revelou padrão geral de cauda: entradas isoladas contra champion neutro em tickers/eventos específicos. O próximo desenvolvimento deve transformar isso em regra explicável de regime/liquidez/evento ou em filtro de concordância com o champion, e só depois repetir uma nova TCN shadow.
- Comandos usados: Python `urllib.request` com `/tmp/phase4_tcn_blocklist_payload.json` e `/tmp/phase4_tcn_blocklist_run_payload.json`; MCP HTTP JSON-RPC em `http://mcpserversisacao.shop/mcp` com consultas em `neural_gate_decisions`, `INFORMATION_SCHEMA.COLUMNS` e `neural_daily_returns`.

## 2026-07-08 20:40 UTC — Próximo passo implementado: filtro de atividade do champion
- Como a TCN com `blocked_tickers` melhorou estabilidade mas ainda deixou caudas novas em `ARML3` e `RCSL3`, implementei uma regra geral para o padrão observado: `require_champion_activity`.
- Quando habilitada, a política neutraliza decisões direcionais da rede em linhas nas quais `champion_net_return` é zero, ou seja, quando o champion estava operacionalmente neutro. Isso testa a hipótese de concordância/compatibilidade com o champion sem expandir blocklist manual ticker a ticker.
- A regra é aplicada depois de `blocked_tickers` e antes do stop intrafold/economia MUEN, entra no manifest/registry, no `training_request`, no hash de família e no sufixo de versão como `ca`.
- Próximo passo operacional pós-deploy: executar uma TCN shadow com `p50/m08/t20/d15/l20`, `blocked_tickers=["ONCO3","BRKM5","CSAN3"]` e `require_champion_activity=true`, três seeds, comparando contra a rodada `bt3_407e4c`.
- Critério: só considerar avanço se remover `fold_catastrofico` mantendo `median_delta > 0`, `stable_across_seeds=true` e trades suficientes; caso contrário, parar Fase 4 e voltar para labels/features/regime.
- Comandos usados: edição de `sisacao8/neural_training.py`, `functions/neural_training/sisacao8/neural_training.py`, `functions/neural_training/main.py`, `sisacao8/neural_evolution.py`, `functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py` e testes associados; `python -m black` nos arquivos alterados.

## 2026-07-09 02:30 UTC — Próximo passo após falha do filtro de champion
- Após deploy, executei dry-run da TCN `p50/m08/t20/d15/l20` com `blocked_tickers=["ONCO3","BRKM5","CSAN3"]` e `require_champion_activity=true`; o dry-run confirmou o sufixo `bt3_407e4c_ca` nos três candidatos.
- A rodada real falhou com HTTP 500 nos três treinos. Diagnóstico via MCP HTTP/JSON-RPC nos logs de `neural_training` confirmou a causa: `ValueError: champion_net_return column is required when require_champion_activity is enabled`.
- Validei via BigQuery `INFORMATION_SCHEMA` que a tabela `neural_eod_training_dataset` não possui `champion_net_return` nem colunas de sinal/champion; os `champion_net_return=0` observados em `neural_daily_returns` eram fallback da avaliação MUEN, não uma trilha real do champion no dataset.
- Apliquei correção de compatibilidade: quando `require_champion_activity=true` mas o snapshot carregado não possui `champion_net_return`, o treinamento desativa esse filtro no alinhamento da configuração para evitar HTTP 500.
- Próximo passo operacional: publicar a correção, mas não repetir a rodada `ca` como se fosse teste válido enquanto o dataset não materializar a atividade real do champion. O próximo desenvolvimento deve adicionar `champion_net_return`/atividade do champion ao dataset point-in-time; só então reexecutar a TCN com `require_champion_activity=true`.
- Comandos usados: Python `urllib.request` com `/tmp/phase4_tcn_blocklist_ca_payload.json` e `/tmp/phase4_tcn_blocklist_ca_run_payload.json`; MCP HTTP JSON-RPC `cloud_run_function_logs` para `neural_training`; MCP BigQuery `INFORMATION_SCHEMA.COLUMNS`; edição de `align_config_to_dataset` e teste de compatibilidade.

## 2026-07-09 03:05 UTC — Próximo passo implementado: champion point-in-time no dataset
- Como a rodada `require_champion_activity=true` revelou que `neural_eod_training_dataset` ainda não tinha atividade/retorno real do champion, implementei a materialização de `champion_net_return` no construtor do dataset neural.
- O `neural_training_dataset` agora carrega trades de uma estratégia champion/baseline a partir de `quant_backtest_trades` (`NEURAL_CHAMPION_STRATEGY_ID`, padrão `baseline_daily_momentum_v1`) e faz join point-in-time por `ticker` e `reference_date`.
- O snapshot passa a carregar `champion_strategy_id`, `champion_strategy_version`, `champion_signal_side`, `champion_net_return` e `champion_trade_active`; quando não há trade do champion, o retorno fica `0.0` e `champion_trade_active=false`.
- Atualizei o DDL de `neural_eod_training_dataset` com migração idempotente para as novas colunas.
- Próximo passo operacional: aplicar o DDL, redeployar `neural_training_dataset`, gerar um novo snapshot do dataset, redeployar/usar `neural_training`, e só então repetir a TCN `bt3+ca` contra o snapshot novo.
- Comandos usados: MCP BigQuery em `quant_backtest_trades`; edição de `functions/neural_training_dataset/main.py`, `infra/bq/17_neural_eod_training_dataset.sql` e testes de dataset.

## 2026-07-09 03:35 UTC — Validação pós-DDL do champion dataset
- O DDL das colunas `champion_*` foi aplicado com sucesso: BigQuery `INFORMATION_SCHEMA` retornou as cinco colunas esperadas em `neural_eod_training_dataset`.
- Executei `neural_training_dataset` para gerar o snapshot `neural_eod_training_dataset_2026-06-27_champion_v1`; a função retornou HTTP 200, `rows=9044`, splits `train=5894`, `validation=750`, `test=900`, `embargo=1500`.
- A validação do snapshot mostrou `champion_active_rows=0`, `champion_return_rows=0` e `champion_strategy_ids=0`; portanto o DDL está correto, mas a Cloud Function publicada ainda não está com o código que faz join em `quant_backtest_trades` e popula as colunas `champion_*`.
- Próximo passo operacional: redeployar `neural_training_dataset` com o commit que materializa `champion_net_return`; depois recriar o snapshot `neural_eod_training_dataset_2026-06-27_champion_v1` com `replace_snapshot=true` e validar novamente `champion_active_rows > 0` antes de rodar TCN `bt3+ca`.
- Comandos usados: MCP HTTP JSON-RPC em `http://mcpserversisacao.shop/mcp` com `INFORMATION_SCHEMA.COLUMNS` e agregação do snapshot; Python `urllib.request` para chamar `neural_training_dataset` com `/tmp/neural_training_dataset_champion_payload.json`.
