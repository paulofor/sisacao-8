# Processo operacional — aprovação de champion neural MUEN

**Data:** 2026-06-25
**Protocolo:** `neural_eod_protocol_v1`
**Objetivo:** transformar uma candidata neural mantida no leaderboard em `champion` aprovado somente depois de evidência econômica MUEN real, auditável e persistida.
**Implementação atual:** `functions/neural_champion_approval` executa `approve_if_passed` e `audit_current_champion`; `evaluate_candidate` ainda deve ser conectado ao avaliador econômico real.

## 1. Estado de partida

O fluxo atual já registra modelos no `neural_model_registry` com status inicial `candidate` e alimenta o leaderboard de evolução neural. Isso não basta para aprovar champion: `keep_candidate` significa apenas que a candidata continua em pesquisa.

A lacuna operacional é executar uma cadeia completa:

```text
candidate/keep_candidate
  -> avaliação econômica por fold/seed/custo
  -> métricas MUEN materializadas
  -> Gate Research passed/rejected
  -> decisão de governança
  -> status approved no registry
  -> champion visível para comparação futura
```

## 2. Princípios obrigatórios

1. **Leaderboard ordena; gate decide.** Nenhum `score_total` aprova champion sozinho.
2. **Sem `approved` sem gate persistido.** O status `approved` só pode ser aplicado quando existir `neural_gate_decisions.passed = true` para a família/candidata.
3. **Comparação econômica é líquida.** A candidata precisa ser comparada contra baseline/champion com custos normais e stress de custo.
4. **Fold e seed são unidades auditáveis.** Métricas agregadas sem rastreio por `fold_id` e `seed` não liberam aprovação.
5. **Holdout, shadow, paper e capital continuam bloqueados.** Aprovar champion de research cria referência oficial; não autoriza operação real automaticamente.
6. **Toda decisão precisa de trilha.** Registrar versão do protocolo, snapshot, modelo, família, gate, critérios falhos e responsável pela promoção.

## 3. Critérios mínimos para selecionar candidata

Uma candidata só entra no processo de aprovação de champion se atender a todos os critérios abaixo:

- está presente no leaderboard atual;
- `decision != 'reject'`;
- possui `model_version`, `dataset_snapshot`, `feature_version` e `label_version` compatíveis com `neural_eod_protocol_v1`;
- artefato existe em `artifact_uri` no `neural_model_registry`;
- métricas básicas não indicam falha técnica evidente, como cobertura nula, ausência de labels ou erro de treino;
- não há candidata já aprovada para o mesmo protocolo/snapshot/família em conflito sem decisão explícita de substituição.

## 4. Etapas do processo

### Etapa 0 — Congelar contexto da rodada

**Objetivo:** impedir que a aprovação misture dados ou contratos diferentes.

Registrar:

- `protocol_version`;
- `dataset_snapshot`;
- `candidate_id`;
- `candidate_family_hash`;
- `model_id`;
- `model_version`;
- `feature_version`;
- `label_version`;
- commit/código usado no avaliador;
- baseline econômico líder e champion vigente, quando houver.

**Saída esperada:** contexto imutável da tentativa de aprovação.

### Etapa 1 — Executar avaliador econômico MUEN

**Objetivo:** gerar `metrics_json.muen_economics` real para a candidata.

Para cada combinação planejada de `fold_id`, `seed` e `cost_multiplier`, executar a candidata no mesmo contrato de labels/trades e calcular:

- trades;
- coverage;
- expectancy líquida;
- mediana de retorno líquido;
- retorno líquido total;
- profit factor;
- max drawdown;
- proporção de trades positivos;
- delta de expectancy contra champion/baseline;
- retornos diários pareados contra champion/baseline.

**Saída esperada:** payload `metrics_json.muen_economics` contendo no mínimo:

```json
{
  "protocol_version": "neural_eod_protocol_v1",
  "candidate_family_hash": "...",
  "seed_count": 3,
  "fold_metrics": [],
  "family_evaluation": {}
}
```

Quando não houver champion neural aprovado ainda, usar a baseline econômica líder aprovada como referência temporária e marcar isso em `metrics_json.reference_type = "economic_baseline"`.

### Etapa 2 — Persistir métricas normativas

**Objetivo:** tornar a avaliação auditável no BigQuery.

Inserir ou atualizar de forma idempotente:

- `neural_fold_metrics`;
- `neural_daily_returns`;
- `neural_family_evaluations`;
- `neural_gate_decisions`.

A persistência deve ser idempotente por:

```text
protocol_version + dataset_snapshot + candidate_family_hash + fold_id + seed + cost_multiplier + code_commit
```

**Saída esperada:** métricas consultáveis por fold/família e decisão de gate materializada.

### Etapa 3 — Executar Gate Research

**Objetivo:** decidir se a candidata pode virar champion de research.

O gate deve retornar `passed` somente quando todos os critérios duros forem cumpridos:

- trades suficientes;
- folds positivos suficientes;
- mediana do delta de expectancy líquida superior à referência;
- pior fold dentro do limite de perda permitido;
- drawdown dentro do limite;
- cenário de custo estressado presente;
- estabilidade entre seeds.

**Saída esperada:** linha em `neural_gate_decisions` com:

- `gate_name = 'research_walk_forward'`;
- `decision_status = 'passed'` ou `rejected`;
- `passed = true` somente se não houver critérios falhos;
- `failed_criteria` preenchido quando reprovado.

### Etapa 4 — Revisão de governança antes de `approved`

**Objetivo:** separar aprovação técnica de alteração de status.

Antes de alterar o registry, validar:

- existe exatamente uma decisão `passed` aplicável à família/modelo;
- não há `muen_economics_missing` na decisão usada;
- a referência comparativa está declarada;
- o snapshot e o protocolo batem com o registry;
- a aprovação não abre holdout, shadow, paper ou produção automaticamente;
- o diário operacional registra motivo, evidência e responsável.

**Saída esperada:** autorização explícita para alterar status do artefato.

### Etapa 5 — Promover registry para `approved`

**Objetivo:** tornar o champion visível para UI e comparações futuras.

Atualizar o `neural_model_registry` apenas para a versão aprovada:

```sql
UPDATE `ingestaokraken.cotacao_intraday.neural_model_registry`
SET
  status = 'approved',
  notes = CONCAT(COALESCE(notes, ''), '\nApproved champion via MUEN Gate Research: <decision_id>')
WHERE model_version = '<model_version>'
  AND status = 'candidate';
```

Se houver champion anterior no mesmo protocolo, a decisão de substituição deve estar registrada. O processo não deve apagar histórico nem sobrescrever métricas antigas.

**Saída esperada:** a UI passa a identificar o modelo como champion aprovado porque existe treino com `status = 'approved'`.

### Etapa 6 — Pós-aprovação

**Objetivo:** manter segurança operacional.

Após aprovar champion:

- registrar no diário principal;
- atualizar `docs/diario/proximo-passo-redes.md`;
- revisar se o passo `Baselines` da jornada saiu de `Em andamento` para pronto para gate formal;
- manter holdout/shadow/paper bloqueados até seus próprios gates;
- usar o novo champion como referência nas próximas rodadas challenger.

## 5. Automação recomendada

Criar uma rotina dedicada, preferencialmente uma Cloud Function ou Cloud Run Job, por exemplo `neural_champion_approval`, com três modos:

### `evaluate_candidate`

Entrada:

```json
{
  "model_version": "...",
  "dataset_snapshot": "...",
  "protocol_version": "neural_eod_protocol_v1",
  "reference_model_version": null,
  "reference_strategy_id": "baseline_daily_breakout_v1",
  "seeds": [20260621, 20260622, 20260623],
  "cost_multipliers": [1.0, 1.5],
  "dry_run": false
}
```

Responsabilidade:

- carregar artefato e dataset;
- executar folds/seeds/custos;
- gerar `muen_economics`;
- persistir métricas e gate.

### `approve_if_passed`

Entrada:

```json
{
  "model_version": "...",
  "decision_id": "...",
  "approved_by": "operador",
  "approval_ticket": "...",
  "dry_run": true
}
```

Responsabilidade:

- validar `neural_gate_decisions.passed = true`;
- validar ausência de critérios falhos;
- simular ou executar update para `status = 'approved'`;
- registrar motivo e referência no `notes`.

### `audit_current_champion`

Responsabilidade:

- listar champions aprovados;
- detectar duplicidade por protocolo/snapshot;
- confirmar se o champion tem gate `passed` associado;
- alertar se houver `approved` sem trilha MUEN.

## 6. Checklist operacional

Antes de aprovar:

- [ ] Candidata está `keep_candidate` ou equivalente no leaderboard.
- [ ] Artefato existe e é carregável.
- [ ] Dataset snapshot e contratos de feature/label são compatíveis.
- [ ] `muen_economics.fold_metrics` foi produzido por fold/seed/custo.
- [ ] `neural_fold_metrics` foi persistida.
- [ ] `neural_daily_returns` foi persistida.
- [ ] `neural_family_evaluations` foi persistida.
- [ ] `neural_gate_decisions` existe com `passed = true`.
- [ ] Não existe falha `muen_economics_missing` na decisão usada.
- [ ] Referência champion/baseline está declarada.
- [ ] Responsável humano/autorização foi registrada.
- [ ] `neural_model_registry.status` foi alterado para `approved` somente depois do gate.

## 7. Critério de parada da próxima implementação

O processo estará implementado quando uma execução real conseguir:

1. selecionar uma candidata `keep_candidate`;
2. produzir `muen_economics` real por fold/seed/custo;
3. persistir fold metrics, daily returns, family evaluation e gate decision;
4. obter `research_walk_forward passed` ou `rejected` sem fallback sintético;
5. em caso `passed`, executar `approve_if_passed` em modo `dry_run` e depois em modo efetivo;
6. exibir um champion aprovado na UI por meio do status `approved` no registry.

## 8. O que não fazer

- Não atualizar `status = 'approved'` manualmente sem `decision_id` de gate aprovado.
- Não promover por `score_total` isolado.
- Não usar holdout para escolher champion de research.
- Não misturar snapshots, features ou labels entre candidato e referência.
- Não trocar HTTP por HTTPS ao acessar o MCP operacional.
- Não liberar paper/capital como consequência automática do status `approved`.
