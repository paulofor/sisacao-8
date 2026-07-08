# Processo operacional — evolução neural em passos

**Objetivo:** transformar a evolução neural em um processo controlado de pesquisa, diagnóstico e promoção governada. A execução manual/orquestrada em passos deve ser usada para descobrir e validar famílias; o Scheduler deve ficar reservado para cadência recorrente de políticas já estabilizadas.

## Princípios

1. **Hipótese antes de automação:** cada rodada deve declarar a hipótese que está sendo testada, por exemplo arquitetura, política `p/m/t/d/l`, mudança de feature, label ou controle de risco.
2. **Shadow primeiro:** toda nova família, arquitetura ou política começa em shadow. Não gerar sinais operacionais nem aprovação automática.
3. **Multi-seed obrigatório:** uma família só pode ser analisada como candidata real se tiver evidência agregada por `candidate_family_hash` e múltiplas seeds.
4. **Gate MUEN imutável:** as iterações podem mudar política, features, arquitetura e filtros, mas não devem relaxar critérios do Gate MUEN para fazer uma candidata passar.
5. **Diagnóstico antes de repetir:** se uma família falha por drawdown, catástrofe de fold, mediana negativa ou instabilidade, a próxima ação deve diagnosticar a causa antes de criar novas variações.
6. **Scheduler só depois de estabilidade:** jobs recorrentes só entram quando a política já passou por dry-run, rodada real pequena, rastreabilidade e critérios mínimos de estabilidade.

## Estados do processo

```text
IDEIA/HIPÓTESE
  -> PREPARAR DADOS/Rastreabilidade
  -> DRY-RUN ORQUESTRADOR
  -> SHADOW PEQUENO MULTI-SEED
  -> VALIDAR MUEN + DIAGNÓSTICO
  -> DECIDIR: DESCARTAR | AJUSTAR | REPETIR | CANDIDATA À PROMOÇÃO
  -> APROVAÇÃO GOVERNADA (manual, se Gate MUEN passed)
  -> SCHEDULER RECORRENTE (somente política madura)
```

## Etapa 1 — Registrar hipótese

Antes de rodar, registrar no diário e/ou no payload:

- `architecture_type`: `tabular_bottleneck_mlp`, `gru_sequence`, `tcn_sequence`, etc.
- Política: `min_directional_probability`, `min_directional_margin`, `max_trades_per_fold`, `max_fold_drawdown_stop`, `sequence_lookback`.
- `candidate_family_hash` estável e legível.
- Critério de sucesso esperado.
- Critério de parada.

Exemplo de família legível:

```text
neural_eod_phase4_tcn_sequence_p50_m08_t20_d15_l20_ticker_v3
```

## Etapa 2 — Preparar dados e rastreabilidade

Antes da rodada real, confirmar que as tabelas necessárias existem e que a trilha de diagnóstico está pronta:

- `neural_fold_metrics`: métricas por fold/seed/custo.
- `neural_family_evaluations`: agregação por família.
- `neural_gate_decisions`: decisão MUEN agregada.
- `neural_daily_returns`: retornos por data e ticker para diagnosticar `worst_delta`.

Se a investigação exige ticker/data/fold, não rodar nova rodada antes de confirmar que `neural_daily_returns.ticker` está persistindo.

## Etapa 3 — Dry-run

Rodar `neural_evolution_orchestrator` com `dry_run=true` para validar:

- `candidate_count` esperado;
- `architecture_types` esperadas;
- `candidate_sources` corretas;
- nomes de `model_version` com sufixos de política (`p/m/t/d/l`);
- `candidate_family_hash` estável.

Se o dry-run não produzir exatamente a família esperada, parar e corrigir payload/código.

## Etapa 4 — Rodada shadow pequena

Executar a menor rodada real útil:

- `max_trials=3` quando o objetivo é multi-seed;
- uma única família/política por rodada;
- `candidate_family_hash` único para a comparação;
- sem promoção automática;
- sem Scheduler dedicado.

A resposta esperada deve incluir:

- `trained_count > 0`;
- `failed_count = 0`;
- `fold_metric_count > 0`;
- `family_evaluation_count >= 1`;
- `gate_decision_count >= 1`;
- `daily_return_count > 0` quando a rodada exige diagnóstico por ticker/data.

## Etapa 5 — Validar Gate MUEN e rastreabilidade

Consultar, no mínimo:

```sql
SELECT
  candidate_family_hash,
  decision_status,
  passed,
  failed_criteria,
  metrics_json.seeds AS seeds,
  metrics_json.total_trades AS total_trades,
  metrics_json.positive_folds AS positive_folds,
  metrics_json.median_delta_expectancy_vs_champion AS median_delta,
  metrics_json.worst_fold_delta_expectancy_vs_champion AS worst_delta,
  metrics_json.max_drawdown AS max_drawdown,
  metrics_json.stable_across_seeds AS stable_across_seeds,
  decided_at
FROM `ingestaokraken.cotacao_intraday.neural_gate_decisions`
WHERE candidate_family_hash = '<candidate_family_hash>'
ORDER BY decided_at DESC
LIMIT 1;
```

Quando houver `daily_return_count > 0`, consultar os piores ticker/data/fold:

```sql
SELECT
  reference_date,
  ticker,
  fold_id,
  seed,
  SUM(model_net_return) AS model_net_return,
  SUM(champion_net_return) AS champion_net_return,
  SUM(delta_net_return) AS delta_net_return,
  SUM(trades) AS trades
FROM `ingestaokraken.cotacao_intraday.neural_daily_returns`
WHERE candidate_family_hash = '<candidate_family_hash>'
GROUP BY reference_date, ticker, fold_id, seed
ORDER BY delta_net_return ASC
LIMIT 50;
```

## Etapa 6 — Decisão de próxima ação

| Resultado | Ação |
| --- | --- |
| `passed=true` e `stableAcrossSeeds=true` | Abrir avaliação de promoção governada; não aprovar automaticamente. |
| Mediana positiva, drawdown ok, só `seeds_instaveis` | Repetir mesma política com mais seeds ou diagnosticar quais seeds/folds quebram. |
| Drawdown alto | Testar controle de risco somente se mediana/edge justificar; caso contrário revisar labels/features. |
| `fold_catastrofico` | Diagnosticar ticker/data/fold antes de nova arquitetura. |
| Mediana negativa | Parar tuning de stop/cap e revisar features/labels/regime. |
| Sem `daily_return_count` quando diagnóstico exige ticker | Redeploy/rastreabilidade antes de repetir pesquisa. |

## Etapa 7 — Quando usar Scheduler

Usar Scheduler somente quando todos forem verdadeiros:

1. dry-run e rodada real pequena já passaram tecnicamente;
2. a família tem rastreabilidade suficiente (`fold_metrics`, `gate_decisions` e, quando necessário, `daily_returns` com ticker);
3. a política não está sendo descoberta, apenas monitorada/reavaliada;
4. não há falhas por falta de schema, payload ou versionamento;
5. orçamento/runtime são previsíveis;
6. a execução recorrente não promove modelos automaticamente.

Enquanto a família estiver em descoberta (como TCN/GRU Fase 4), preferir rodadas manuais e curtas em vez de Scheduler.

## Etapa 8 — Registro obrigatório

Ao final de cada ciclo, registrar em `docs/diario/registros1.md` e atualizar `docs/diario/proximo-passo-redes.md` com:

- payload/família/política executada;
- contadores da função (`trained_count`, `failed_count`, `fold_metric_count`, etc.);
- decisão MUEN;
- principais métricas;
- conclusão operacional;
- próximo passo e critério de parada.
