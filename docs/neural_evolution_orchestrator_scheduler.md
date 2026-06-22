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
- Service account do Scheduler com permissão de invocar Cloud Functions Gen2/Cloud Run.
- Service account de runtime da função com permissão de ler/escrever BigQuery e invocar `neural_training` se ela estiver protegida.

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

## Configuração do Cloud Scheduler

Exemplo semanal, segunda-feira às 06:00 no horário de São Paulo:

```bash
gcloud scheduler jobs create http neural-evolution-weekly \
  --project=ingestaokraken \
  --location=us-east1 \
  --schedule='0 6 * * 1' \
  --time-zone='America/Sao_Paulo' \
  --uri='https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator' \
  --http-method=POST \
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":10,"max_runtime_minutes":240,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
  --oidc-service-account-email='agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com' \
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
  --headers='Content-Type=application/json' \
  --message-body='{"strategy":"deterministic_phase1","budget":{"max_trials":10,"max_runtime_minutes":240,"max_parameter_count":150000,"max_layers":4,"random_seed":20260621}}' \
  --oidc-service-account-email='agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com' \
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
