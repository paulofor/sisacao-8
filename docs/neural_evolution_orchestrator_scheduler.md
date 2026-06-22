# Scheduler da evolução neural determinística

Este runbook descreve como acionar a Cloud Function HTTP `neural_evolution_orchestrator`, que executa uma rodada controlada de evolução neural EOD.

## O que a função faz

1. Lê o snapshot mais recente de `cotacao_intraday.neural_eod_training_dataset`, salvo quando `dataset_snapshot` é enviado no payload.
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

## Deadline do Scheduler

O Cloud Scheduler cria jobs HTTP com `attemptDeadline` padrão de 180 segundos. Esse valor é curto para a evolução neural, porque a função pode chamar `neural_training` várias vezes na mesma rodada. Configure `--attempt-deadline=1800s` para permitir até 30 minutos por tentativa, que é o limite prático recomendado para este agendamento HTTP.

Se o job já foi criado e a saída mostrou `attemptDeadline: 180s`, atualize-o:

```bash
gcloud scheduler jobs update http neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --attempt-deadline=1800s
```

Para rodadas maiores que 30 minutos, reduza `max_trials` ou evolua o orquestrador para enfileirar treinos de forma assíncrona em vez de manter uma única requisição HTTP aberta.

## Configuração rápida do Cloud Scheduler sem OIDC

Use esta forma quando a função estiver publicada com invocação pública (`--allow-unauthenticated`), que é o comportamento atual do workflow de deploy.

```bash
gcloud scheduler jobs create http neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":10,"max_runtime_minutes":240,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}'
```

## Configuração do Cloud Scheduler com OIDC

Use esta forma quando quiser manter o job autenticado. Antes, confirme/crie `sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com` e conceda `roles/run.invoker`, conforme a seção de diagnóstico.

```bash
gcloud scheduler jobs create http neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":10,"max_runtime_minutes":240,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
  --oidc-service-account-email='sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com' \
  --oidc-token-audience='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator'
```

Para alterar um job existente:

```bash
gcloud scheduler jobs update http neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --attempt-deadline=1800s \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":10,"max_runtime_minutes":240,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
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
