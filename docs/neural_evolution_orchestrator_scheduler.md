# Scheduler da evolução neural determinística

Este runbook descreve como acionar a Cloud Function HTTP `neural_evolution_orchestrator`, que executa uma rodada controlada de evolução neural EOD.

## O que a função faz

1. Lê o snapshot completo mais recente de `cotacao_intraday.neural_eod_training_dataset`, com splits `train`, `validation` e `test`, salvo quando `dataset_snapshot` é enviado no payload.
2. Gera candidatos determinísticos com orçamento limitado (`max_trials`, `max_runtime_minutes`, `max_parameter_count`, `max_layers`, `random_seed`).
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
  "strategy": "deterministic_phase1",
  "budget": {
    "max_trials": 10,
    "max_runtime_minutes": 240,
    "max_parameter_count": 150000,
    "max_layers": 4,
    "random_seed": 20260621
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

Estado esperado: `state: ENABLED`, `schedule: 0 6 * * *`, `timeZone: America/Sao_Paulo`, URI apontando para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator` e `attemptDeadline` próximo de `1800s`.

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


## Operação recorrente

Para evolução contínua com controle, a cadência recomendada passa a ser diária (`neural-evolution-daily`) com orçamento menor por rodada. Essa configuração avalia redes pendentes com mais rapidez sem concentrar custo/runtime em uma única execução semanal.

Use `max_trials` entre 2 e 5 para controlar custo e duração; comece com `max_trials=3` e aumente apenas se as execuções ficarem abaixo do `attempt-deadline=1800s` e as métricas continuarem estáveis. Rodadas manuais continuam úteis para antecipar uma triagem pontual ou recuperar uma execução perdida.

## Alteração via MCP Server

Quando a versão do MCP que expõe a tool `neural_evolution_daily_scheduler_apply` estiver publicada, prefira alterar o Scheduler por JSON-RPC HTTP no endpoint `http://mcpserversisacao.shop/mcp`. A tool cria ou atualiza `neural-evolution-daily` com agenda diária, `max_trials=3`, `max_runtime_minutes=120` e pausa o job semanal após a aplicação:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "neural_evolution_daily_scheduler_apply",
    "arguments": {
      "location": "us-east1",
      "schedule": "0 6 * * *",
      "max_trials": 3,
      "max_runtime_minutes": 120,
      "pause_weekly": true
    }
  }
}
```

Para operações administrativas genéricas no Cloud Scheduler, a versão atualizada do MCP também expõe `cloud_scheduler_job_write`, que aceita `action` (`create`, `update`, `pause`, `resume`, `run` ou `delete`) e executa o respectivo `gcloud scheduler jobs ...` no runtime autenticado do MCP.

Se o job semanal `neural-evolution-weekly` já existir, não mantenha dois Schedulers ativos chamando a mesma função sem necessidade. Depois de criar e validar o `neural-evolution-daily`, pause ou remova o semanal:

```bash
gcloud scheduler jobs pause neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1
```

## Configuração rápida do Cloud Scheduler sem OIDC

Use esta forma quando a função estiver publicada com invocação pública (`--allow-unauthenticated`), que é o comportamento atual do workflow de deploy.

```bash
gcloud scheduler jobs create http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}'
```

## Configuração do Cloud Scheduler com OIDC

Use esta forma quando quiser manter o job autenticado. Antes, confirme/crie `sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com` e conceda `roles/run.invoker`, conforme a seção de diagnóstico.

```bash
gcloud scheduler jobs create http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
  --oidc-service-account-email='sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com' \
  --oidc-token-audience='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator'
```

Para alterar um job existente:

```bash
gcloud scheduler jobs update http neural-evolution-daily \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * *' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --update-headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":3,"max_runtime_minutes":120,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
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
