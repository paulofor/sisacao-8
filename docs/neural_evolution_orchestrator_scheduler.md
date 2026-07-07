# Scheduler da evolução neural determinística

Este runbook descreve como acionar a Cloud Function HTTP `neural_evolution_orchestrator`, que executa uma rodada controlada de evolução neural EOD.

## O que a função faz

1. Lê o snapshot completo mais recente de `cotacao_intraday.neural_eod_training_dataset`, com splits `train`, `validation` e `test`, salvo quando `dataset_snapshot` é enviado no payload.
2. Gera candidatos conforme a estratégia: `deterministic_phase1` cria novas arquiteturas determinísticas; `deterministic_phase2` lê candidatos mantidos no leaderboard, consolida famílias semelhantes antes de selecionar pais e gera mutações/repetições controladas para a próxima avaliação.
3. Grava a rodada em `neural_evolution_runs`.
4. Grava as configurações em `neural_candidate_configs`.
5. Chama `neural_training` uma vez por candidato.
6. Lê as métricas geradas em `neural_model_registry`.
7. Calcula score/decisão e grava `neural_candidate_evaluations`, alimentando `vw_neural_evolution_leaderboard`.

## Pré-requisitos

- DDL `infra/bq/21_neural_evolution.sql` aplicado no BigQuery.
- Cloud Function `neural_training` publicada e funcional.
- Cloud Function `neural_evolution_orchestrator` publicada pelo workflow de deploy.
- Para agendamento sem autenticação OIDC: a função precisa estar com invocação pública, como no workflow atual que usa `--allow-unauthenticated`.
- Para agendamento com OIDC: a service account usada no `--oidc-service-account-email` precisa existir antes da criação do job e possuir permissão `roles/run.invoker` na função/serviço Gen2.

## Diagnóstico do erro `NOT_FOUND` no `gcloud scheduler jobs create http`

Se o comando falhar com:

```text
ERROR: (gcloud.scheduler.jobs.create.http) NOT_FOUND: Requested entity was not found.
```

e o comando usa `--oidc-service-account-email`, a causa mais provável é que a service account informada não existe no projeto. O exemplo antigo usava `agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com`; neste repositório, o Terraform de IAM usa por padrão `sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com`.

Valide antes de criar o Scheduler:

```bash
gcloud iam service-accounts describe \
  sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com \
  --project=ingestaokraken
```

Se não existir, crie a conta:

```bash
gcloud iam service-accounts create sa-scheduler-invoker \
  --project=ingestaokraken \
  --display-name='Sisacao scheduler invoker'
```

Conceda permissão de invocação na Cloud Function Gen2/Cloud Run service:

```bash
gcloud run services add-iam-policy-binding neural_evolution_orchestrator \
  --project=ingestaokraken \
  --region=us-east1 \
  --member='serviceAccount:sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com' \
  --role='roles/run.invoker'
```

> Observação: se a função ainda não tiver sido publicada, o comando de IAM acima também pode falhar. Nesse caso, publique primeiro a função pelo workflow ou por `gcloud functions deploy`.

## Payload recomendado

```json
{
  "strategy": "deterministic_phase2",
  "budget": {
    "max_trials": 1,
    "max_runtime_minutes": 45,
    "max_parameter_count": 150000,
    "max_layers": 4,
    "random_seed": 20260621
  },
  "phase2": {
    "top_fraction": 1.0,
    "parent_limit": 10,
    "max_parents_per_family": 1,
    "include_seed_repeats": false,
    "controlled_diversity": true
  }
}
```

Para fixar um snapshot específico:

```json
{
  "dataset_snapshot": "neural_eod_training_dataset_2026-06-18_phase0_20260621",
  "evolution_run_id": "neural_evolution_phase1_20260621",
  "model_version_prefix": "neural_eod_mlp_evo1_20260621",
  "strategy": "deterministic_phase1",
  "budget": {
    "max_trials": 10,
    "random_seed": 20260621
  }
}
```

## Teste manual

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"strategy":"deterministic_phase1","budget":{"max_trials":2,"random_seed":20260621}}'
```

Use `dry_run=true` para validar geração de candidatos sem gravar no BigQuery e sem chamar `neural_training`:

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"dry_run":true,"budget":{"max_trials":2,"random_seed":20260621}}'
```


## Verificar existência do Scheduler

Para confirmar no GCP se o job existe e está habilitado, execute:

```bash
gcloud scheduler jobs describe neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --format='yaml(name,state,schedule,timeZone,attemptDeadline,httpTarget.uri,httpTarget.httpMethod,httpTarget.body,nextRunTime,lastAttemptTime)'
```

Para listar apenas jobs relacionados à evolução neural:

```bash
gcloud scheduler jobs list \
  --project=ingestaokraken \
  --location=us-east1 \
  --filter='name:neural-evolution OR httpTarget.uri:neural_evolution_orchestrator'
```

Estado esperado para a cadência solicitada de meia em meia hora: `state: ENABLED`, `schedule: */30 * * * *`, `timeZone: America/Sao_Paulo`, URI apontando para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator` e `attemptDeadline` próximo de `1800s`.

## Deadline do Scheduler

O Cloud Scheduler cria jobs HTTP com `attemptDeadline` padrão de 180 segundos. Esse valor é curto para a evolução neural, porque a função pode chamar `neural_training` várias vezes na mesma rodada. Configure `--attempt-deadline=1800s` para permitir até 30 minutos por tentativa, que é o limite prático recomendado para este agendamento HTTP.

Se o job já foi criado e a saída mostrou `attemptDeadline: 180s`, atualize-o:

```bash
gcloud scheduler jobs update http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --attempt-deadline=1800s
```

Para rodadas maiores que 30 minutos, reduza `max_trials` ou evolua o orquestrador para enfileirar treinos de forma assíncrona em vez de manter uma única requisição HTTP aberta.



## Automação após Gate MUEN rejeitado

Quando uma candidata neural real é avaliada pelo Gate MUEN e retorna `rejected`,
não rode novamente a sequência manual `neural_training_dataset` → `neural_training`
→ `neural_champion_approval` para cada tentativa. O fluxo recorrente deve ser:

1. manter um snapshot v2 válido em `neural_eod_training_dataset`;
2. deixar o Cloud Scheduler `neural-evolution-daily` acionar
   `neural_evolution_orchestrator`;
3. o orquestrador gerar/mutar candidatos (`deterministic_phase2`), chamar
   `neural_training`, ler `metrics_json.muen_economics` no registry e persistir
   as tabelas MUEN (`neural_fold_metrics`, `neural_family_evaluations` e
   `neural_gate_decisions`);
4. revisar apenas decisões `passed` para então executar o fluxo governado
   `approve_if_passed` em dry-run e depois efetivo.

A aprovação de champion não deve ser agendada automaticamente: `approve_if_passed`
continua sendo uma etapa governada e só deve ser executada quando existir uma
decisão `passed` auditável.

Para antecipar uma rodada sem esperar a próxima janela do Scheduler, dispare o job
já existente em vez de chamar manualmente cada função:

```bash
gcloud scheduler jobs run neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1
```

Se precisar rodar diretamente a função para uma triagem pontual, use:

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"strategy":"deterministic_phase2","budget":{"max_trials":1,"max_runtime_minutes":45,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621},"phase2":{"top_fraction":1.0,"parent_limit":10,"max_parents_per_family":1,"include_seed_repeats":false,"controlled_diversity":true}}'
```

## Operação recorrente

Para evolução contínua com controle, a cadência solicitada passa a ser de meia em meia hora (`*/30 * * * *`) no job `neural-evolution-daily`, com orçamento menor por rodada. Essa configuração avalia redes pendentes com mais rapidez sem concentrar custo/runtime em uma única execução semanal.

Use `max_trials=1` como padrão para a cadência de 30 minutos. A execução passa a ter até 48 tentativas por dia, então aumentar o orçamento por rodada pode multiplicar custo e concorrência rapidamente. Se precisar ampliar, faça isso apenas depois de confirmar que cada execução termina bem abaixo de `attempt-deadline=1800s`, que não há sobreposição de treinos e que as métricas/custos continuam estáveis. Rodadas manuais continuam úteis para antecipar uma triagem pontual ou recuperar uma execução perdida.

A diversidade controlada fica habilitada por `phase2.controlled_diversity=true`: quando mutações e variantes simples de arquitetura se esgotarem, o orquestrador tenta combinações novas e limitadas de topologia MLP + hiperparâmetros antes de cair para repetição pura com seed fresca.

## Alteração via MCP Server

Quando a versão do MCP que expõe a tool `neural_evolution_daily_scheduler_apply` estiver publicada, prefira alterar o Scheduler por JSON-RPC HTTP no endpoint `http://mcpserversisacao.shop/mcp`. A tool cria ou atualiza `neural-evolution-daily` com agenda de meia em meia hora, `strategy=deterministic_phase2`, `max_trials=1`, `max_runtime_minutes=45` e pausa o job semanal após a aplicação:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "neural_evolution_daily_scheduler_apply",
    "arguments": {
      "location": "us-east1",
      "schedule": "*/30 * * * *",
      "strategy": "deterministic_phase2",
      "max_trials": 1,
      "max_runtime_minutes": 45,
      "phase2": {
        "top_fraction": 1.0,
        "parent_limit": 10,
        "max_parents_per_family": 1,
        "include_seed_repeats": false,
        "controlled_diversity": true
      },
      "pause_weekly": true
    }
  }
}
```

Para operações administrativas genéricas no Cloud Scheduler, a versão atualizada do MCP também expõe `cloud_scheduler_job_write`, que aceita `action` (`create`, `update`, `pause`, `resume`, `run` ou `delete`) e executa o respectivo `gcloud scheduler jobs ...` no runtime autenticado do MCP.

Se o job semanal `neural-evolution-weekly` já existir, não mantenha dois Schedulers ativos chamando a mesma função sem necessidade. Depois de criar e validar o `neural-evolution-daily`, pause ou remova o job semanal antigo:

```bash
gcloud scheduler jobs pause neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1
```

## Diagnóstico de `NOT_FOUND` no update

Se `gcloud scheduler jobs update http neural-evolution-daily` retornar `NOT_FOUND`, não assuma imediatamente que o job não existe. Verifique primeiro:

```bash
gcloud scheduler jobs describe neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1
```

Se o `describe` também retornar `NOT_FOUND`, as causas mais prováveis são:

1. a conta ativa do `gcloud` não tem permissão para ver/atualizar Cloud Scheduler no projeto;
2. o job foi criado em outro projeto/location;
3. o comando incluiu `--oidc-service-account-email` com uma service account inexistente ou sem permissão de uso.

Para este ambiente, o job `neural-evolution-daily` foi verificado via MCP/GCP em `ingestaokraken/us-east1`. Portanto, se o seu terminal local retornar `NOT_FOUND`, valide a conta ativa e solicite/atribua pelo menos `roles/cloudscheduler.admin` no projeto antes de repetir o update. Se for usar OIDC, a conta que executa o comando também precisa poder usar a service account invocadora (`roles/iam.serviceAccountUser` sobre `sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com`).

Como o job atual pode estar configurado sem OIDC quando a função está pública, prefira primeiro o update sem OIDC da seção rápida. Use o bloco com OIDC somente após confirmar que a service account existe e que sua conta pode usá-la.

## Configuração rápida do Cloud Scheduler sem OIDC

Use esta forma quando a função estiver publicada com invocação pública (`--allow-unauthenticated`), que é o comportamento atual do workflow de deploy.

```bash
gcloud scheduler jobs create http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase2","budget":{"max_trials":1,"max_runtime_minutes":45,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621},"phase2":{"top_fraction":1.0,"parent_limit":10,"max_parents_per_family":1,"include_seed_repeats":false,"controlled_diversity":true}}'
```

Para alterar o job existente sem OIDC:

```bash
gcloud scheduler jobs update http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --update-headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase2","budget":{"max_trials":1,"max_runtime_minutes":45,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621},"phase2":{"top_fraction":1.0,"parent_limit":10,"max_parents_per_family":1,"include_seed_repeats":false,"controlled_diversity":true}}'
```

## Configuração do Cloud Scheduler com OIDC

Use esta forma quando quiser manter o job autenticado. Antes, confirme/crie `sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com` e conceda `roles/run.invoker`, conforme a seção de diagnóstico.

```bash
gcloud scheduler jobs create http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase2","budget":{"max_trials":1,"max_runtime_minutes":45,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621},"phase2":{"top_fraction":1.0,"parent_limit":10,"max_parents_per_family":1,"include_seed_repeats":false,"controlled_diversity":true}}' \
  --oidc-service-account-email='sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com' \
  --oidc-token-audience='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator'
```

Para alterar um job existente:

```bash
gcloud scheduler jobs update http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --update-headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase2","budget":{"max_trials":1,"max_runtime_minutes":45,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621},"phase2":{"top_fraction":1.0,"parent_limit":10,"max_parents_per_family":1,"include_seed_repeats":false,"controlled_diversity":true}}' \
  --oidc-service-account-email='sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com' \
  --oidc-token-audience='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator'
```

## Validação após execução

```bash
curl -sS 'http://34.194.252.70/api/ops/neural/evolution/leaderboard'
```

Também valide no BigQuery que há linhas em:

- `cotacao_intraday.neural_evolution_runs`
- `cotacao_intraday.neural_candidate_configs`
- `cotacao_intraday.neural_candidate_evaluations`
- `cotacao_intraday.vw_neural_evolution_leaderboard`

## Agendamento recomendado para Fase 3

A Fase 3 (`strategy=phase3_new_families`) não exige um novo Cloud Scheduler para funcionar: a mesma Cloud Function `neural_evolution_orchestrator` já seleciona a estratégia pelo payload HTTP. Portanto, uma execução manual ou um update temporário do job `neural-evolution-daily` tecnicamente bastam.

Operacionalmente, porém, não substitua o payload recorrente de Fase 2 sem uma decisão explícita. O job `neural-evolution-daily` deve continuar cuidando da evolução incremental/mutação do MLP champion. Para Fase 3, prefira uma das duas opções seguras:

1. **Primeira rodada:** chamada manual com `dry_run=true`, depois uma chamada manual treinada pequena.
2. **Recorrência controlada:** criar um job separado, por exemplo `neural-evolution-phase3-weekly`, inicialmente `PAUSED` ou com cadência semanal, para evitar concorrência/custo com o job diário.

Payload de dry-run recomendado:

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"dry_run":true,"strategy":"phase3_new_families","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}'
```

Exemplo de Scheduler separado, sem OIDC enquanto a função estiver pública:

```bash
gcloud scheduler jobs create http neural-evolution-phase3-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 8 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"phase3_new_families","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  --attempt-deadline=1800s
```

Se criar esse job antes da validação inicial, deixe-o pausado até a primeira rodada manual passar pelo MUEN:

```bash
gcloud scheduler jobs pause neural-evolution-phase3-weekly \
  --project=ingestaokraken \
  --location=us-east1
```

## Teste manual da Fase 3

Use este roteiro depois de publicar as versões atualizadas de `functions/neural_training` e `functions/neural_evolution_orchestrator`.

### 1. Dry-run sem treino e sem escrita

Valida se o orquestrador consegue gerar candidatas Fase 3 e se o payload contém `strategy=phase3_new_families`.

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"dry_run":true,"strategy":"phase3_new_families","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  | python -m json.tool
```

Resultado esperado: HTTP 200, `status=ok`, `dry_run=true`, `candidate_count` entre 1 e 3 e modelos com prefixo `neural_eod_phase3_`.

### 2. Rodada pequena sem chamar treino

Use esta etapa apenas se quiser materializar a rodada/configuração no BigQuery, mas sem executar TensorFlow ainda. Ela exige que os `model_version` gerados já existam no `neural_model_registry`; se não existirem, a função pode falhar ao tentar buscar o registry. Para um primeiro teste operacional, prefira pular esta etapa e ir direto para a etapa 3 com `max_trials=1`.

A Fase 3 também usa diversidade controlada: após as configurações base de `residual_mlp`, `wide_deep_mlp` e `tabular_bottleneck_mlp` já existirem, novas rodadas variam learning rate, dropout, batch size, epochs e class weight antes de se tornarem apenas repetições por seed.

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"strategy":"phase3_new_families","train_candidates":false,"budget":{"max_trials":1,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  | python -m json.tool
```

### 3. Primeiro treino real mínimo

Executa apenas uma família nova. Use fora de horário crítico e acompanhe logs/custos.

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{"strategy":"phase3_new_families","budget":{"max_trials":1,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  | python -m json.tool
```

Resultado esperado: `trained_count=1`, `failed_count=0`, linha nova em `neural_candidate_configs`, linha nova em `neural_model_registry`, linha nova em `neural_candidate_evaluations` e, quando houver payload MUEN, decisão em `neural_gate_decisions`.

### 4. Conferência pela API publicada

```bash
curl -sS 'http://34.194.252.70/api/ops/neural/evolution/leaderboard' \
  | python -m json.tool
```

Procure entradas recentes com `candidateSource`/`candidate_source` igual a `phase3_family` ou `modelVersion` começando com `neural_eod_phase3_`.

### 5. Conferência via BigQuery/MCP

Quando precisar validar diretamente no BigQuery, use o MCP por JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` e a ferramenta `bigquery_query`. Consulta read-only sugerida:

```sql
SELECT
  candidate_source,
  model_id,
  model_version,
  architecture_json,
  hyperparameters_json,
  created_at
FROM `ingestaokraken.cotacao_intraday.neural_candidate_configs`
WHERE candidate_source = 'phase3_family'
ORDER BY created_at DESC
LIMIT 10;
```

Não execute `approve_if_passed` automaticamente. Qualquer aprovação continua manual/governada e só deve ocorrer se o Gate MUEN retornar `passed`.

### Diagnóstico de deploy desatualizado

Se o dry-run com `strategy=phase3_new_families` retornar candidatos como `neural_eod_mlp_evo1_<data>_01` e não trouxer `candidate_sources=["phase3_family"]`/`architecture_types`, a Cloud Function publicada ainda está com uma versão anterior do orquestrador. Nesse caso, não avance para treino real de Fase 3: publique novamente `functions/neural_evolution_orchestrator` e `functions/neural_training`, repita o dry-run e só prossiga quando o retorno indicar explicitamente:

- `strategy: "phase3_new_families"`;
- `candidate_sources` contendo apenas `phase3_family`;
- `architecture_types` contendo uma ou mais famílias novas, como `residual_mlp`, `wide_deep_mlp` ou `tabular_bottleneck_mlp`;
- `candidates` com prefixo `neural_eod_phase3_`.

## Scheduler Fase 3 a cada 30 minutos

Use este job separado apenas depois de confirmar, em dry-run, que a Cloud Function publicada retorna `candidate_sources=["phase3_family"]` e candidatos com prefixo `neural_eod_phase3_`. Ele não substitui o `neural-evolution-daily` da Fase 2.

Criação sem OIDC, adequada enquanto `neural_evolution_orchestrator` estiver pública:

```bash
gcloud scheduler jobs create http neural-evolution-phase3-30m \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"phase3_new_families","budget":{"max_trials":1,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  --attempt-deadline=1800s
```

Se o job já existir, use update:

```bash
gcloud scheduler jobs update http neural-evolution-phase3-30m \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='*/30 * * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --update-headers='Content-Type=application/json' \
  --message-body='{"strategy":"phase3_new_families","budget":{"max_trials":1,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260629}}' \
  --attempt-deadline=1800s
```

Depois de criar, valide:

```bash
gcloud scheduler jobs describe neural-evolution-phase3-30m \
  --project=ingestaokraken \
  --location=us-east1 \
  --format='yaml(name,state,schedule,timeZone,attemptDeadline,httpTarget.uri,httpTarget.httpMethod,httpTarget.body,nextRunTime,lastAttemptTime)'
```

## Fase 4 recorrente em shadow — início manual pós-deploy

Use esta sequência depois de publicar `functions/neural_training` e `functions/neural_evolution_orchestrator` com suporte a `phase4_recurrent_shadow`. A Fase 4 deve começar manualmente e em shadow; não reutilize o Scheduler de Fase 2/Fase 3 antes de confirmar dry-run e primeira rodada real pequena.

### 1. Dry-run obrigatório

Este comando não treina nem grava resultados de treino; ele valida se a função publicada reconhece a estratégia e gera as três famílias recorrentes/temporais esperadas.

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{
    "strategy": "phase4_recurrent_shadow",
    "dry_run": true,
    "budget": {
      "max_trials": 3,
      "max_runtime_minutes": 180,
      "max_parameter_count": 150000,
      "max_layers": 4,
      "random_seed": 20260707
    }
  }' | python -m json.tool
```

Critérios mínimos para avançar:

- `status` igual a `ok`;
- `dry_run` igual a `true`;
- `candidate_count` igual a `3`;
- `architecture_types` contendo `gru_sequence`, `lstm_sequence` e `tcn_sequence`;
- `candidates` com prefixo `neural_eod_phase4_` e sufixo de política `p50_m08_t35_l20`.

### 2. Primeira rodada real pequena

Depois do dry-run passar, execute uma rodada real pequena com as três famílias. Esta chamada treina e grava registros de candidato, métricas e decisões MUEN. Ela continua em shadow/research e não aprova modelos automaticamente.

```bash
curl -sS -X POST 'https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  -H 'Content-Type: application/json' \
  --data '{
    "strategy": "phase4_recurrent_shadow",
    "budget": {
      "max_trials": 3,
      "max_runtime_minutes": 180,
      "max_parameter_count": 150000,
      "max_layers": 4,
      "random_seed": 20260707
    }
  }' | python -m json.tool
```

Resultado esperado: `trained_count` maior que zero, `failed_count` igual a `0` ou, se houver falha, investigar antes de repetir; `gate_decision_count` deve refletir avaliações MUEN emitidas. Não execute `approve_if_passed`.

### 3. Validação pela API operacional

```bash
curl -sS 'http://34.194.252.70/api/ops/neural/training-runs' \
  | python -m json.tool

curl -sS 'http://34.194.252.70/api/ops/neural/gate-decisions' \
  | python -m json.tool
```

Procure `modelVersion`/`candidateFamilyHash` com prefixos `neural_eod_phase4_`, arquiteturas `gru_sequence`, `lstm_sequence` ou `tcn_sequence`, `sequence_lookback=20` nos hiperparâmetros e decisão MUEN auditável.

### 4. Scheduler opcional separado

Só crie Scheduler da Fase 4 depois de dry-run e primeira rodada real pequena passarem. Use um job separado para não alterar o `neural-evolution-daily` existente.

```bash
gcloud scheduler jobs create http neural-evolution-phase4-shadow-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 8 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"phase4_recurrent_shadow","budget":{"max_trials":3,"max_runtime_minutes":180,"max_parameter_count":150000,"max_layers":4,"random_seed":20260707}}' \
  --attempt-deadline=1800s
```

Enquanto a função estiver pública, mantenha o comando sem OIDC. Se a função passar a exigir autenticação, valide service account, `roles/run.invoker` e `roles/iam.serviceAccountUser` antes de adicionar OIDC.
