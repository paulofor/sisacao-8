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
