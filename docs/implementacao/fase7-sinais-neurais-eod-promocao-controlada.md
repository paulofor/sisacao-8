# Fase 7 — Promoção controlada dos sinais neurais EOD

Esta fase fecha o ciclo inicial do plano neural com uma camada explícita de promoção. A regra principal é conservadora: nenhum modelo neural deve substituir sozinho o fluxo atual; uma aprovação válida libera apenas o modo `hybrid`, mantendo `heuristic` como fallback operacional.

## Entregáveis

- Código reutilizável: `sisacao8/neural_promotion.py`.
- Script BigQuery: `infra/bq/20_neural_eod_controlled_promotion.sql`.
- Testes unitários: `tests/test_neural_promotion.py`.

## Critérios iniciais

A configuração `neural_eod_controlled_promotion/v1` exige:

| Critério | Valor inicial |
|---|---:|
| Profit factor OOS mínimo | 1,15 |
| Win rate OOS mínimo | 52% |
| Profit factor no paper mínimo | 1,10 |
| Win rate no paper mínimo | 50% |
| Dias mínimos de paper | 120 |
| Trades mínimos em paper | 50 |
| Drawdown máximo no paper | 12% |
| Fill rate mínimo | 40% |
| Divergência média máxima contra backtest | 5% |
| Aprovações explícitas mínimas | 1 |

## Fluxo de decisão

1. Consolidar métricas fora da amostra e de paper trading para `model_id/model_version`.
2. Coletar aprovação explícita de responsável humano, registrada como approver/ticket.
3. Executar `evaluate_neural_promotion`.
4. Registrar a decisão em `neural_eod_promotion_decisions`.
5. Consumir `vw_neural_eod_promotion_gate` para determinar a fonte segura:
   - aprovado: `safe_signal_source = hybrid`;
   - bloqueado ou sem decisão: `safe_signal_source = heuristic`.

## Garantias operacionais

- A promoção aprovada não altera pesos, features nem thresholds do modelo.
- A promoção aprovada não força modo `neural` puro.
- O fallback declarado é sempre `heuristic`.
- Decisões bloqueadas ficam auditáveis com `failed_criteria`.
- A view `vw_neural_eod_active_promotion` expõe somente a última promoção aprovada por família de modelo.

## Próximos passos

1. Aplicar `infra/bq/20_neural_eod_controlled_promotion.sql` no BigQuery.
2. Criar automação operacional que leia `vw_neural_eod_promotion_gate` antes de configurar `SIGNAL_SOURCE`.
3. Registrar aprovações reais com ticket externo quando houver evidência suficiente de paper trading.
4. Manter rollback documentado para `SIGNAL_SOURCE=heuristic`.
