# Fase 0 — Hipótese econômica MUEN v1

**Documento normativo de origem:** [`docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`](../planejamento/metodo-unificado-evolucao-neural-sisacao.md)  
**Status da Fase 0:** executada e congelada para orientar as Fases 1–3  
**Data de execução:** 2026-06-24  
**Protocolo declarado:** `neural_eod_protocol_v1`  
**Hipótese declarada:** `eod_barrier_direction_v2`

A Fase 0 registra a hipótese econômica antes de qualquer novo treino, mutação ou promoção. O objetivo é impedir que a evolução neural comece por aumento de complexidade e garantir que as próximas fases tenham um contrato econômico verificável.

## 1. Declaração da hipótese

Usando somente dados disponíveis no fechamento do pregão `D`, estimar ações da B3 com vantagem líquida esperada para operações direcionais `BUY` e `SELL`, com decisão EOD, tentativa de entrada limitada a partir de `D+1`, alvo, stop e expiração versionados, horizonte máximo de 15 pregões e comparação obrigatória contra champion, heurística atual e baselines simples.

A rede neural só é justificada se capturar interações não lineares entre retorno, volatilidade, range, gap, volume, liquidez, regime e distâncias técnicas que não sejam explicadas por baselines lineares ou heurísticas equivalentes.

## 2. Padrão de mercado pretendido

- **Tipo de padrão:** combinação de momentum curto, reversão parcial, compressão/expansão de volatilidade, liquidez e regime.
- **Hipótese operacional:** determinadas configurações de preço, volume e regime no fechamento de `D` elevam a probabilidade de atingir uma barreira de retorno antes da barreira oposta ou da expiração.
- **Risco principal da hipótese:** sobreajuste em eventos raros, vazamento temporal, dependência de poucos ativos líquidos e sinais cuja vantagem desaparece após custos.
- **Critério de rejeição antecipada:** se baselines simples com o mesmo universo, custos e horizonte entregarem desempenho líquido equivalente ou superior, a rede neural não deve avançar.

## 3. Universo point-in-time

- **Mercado:** ações listadas na B3.
- **Fonte operacional:** tabelas BigQuery já mapeadas do projeto, com destaque para `cotacao_intraday.acao_bovespa`, `cotacao_intraday.cotacao_ohlcv_diario`, `cotacao_intraday.feriados_b3` e agregações intraday quando necessárias para auditoria de execução.
- **Regra temporal:** a composição do universo deve representar o que era conhecido na data de decisão, sem sobrevivorship bias intencional.
- **Elegibilidade inicial:** ativo com histórico suficiente para features, preço/volume válidos, liquidez mínima parametrizável, ausência de inconsistências OHLCV graves e calendário compatível com pregões B3.
- **Exclusões iniciais:** ativos sem dados suficientes, com volume financeiro insuficiente, dados ausentes críticos, duplicidades não resolvidas ou eventos corporativos não tratáveis no snapshot.

## 4. Instante de decisão e dados permitidos

- **Instante da decisão:** após o fechamento de `D`.
- **Dados permitidos:** somente informações conhecidas até o fechamento de `D`, incluindo candles diários encerrados, indicadores calculados com janelas passadas, calendário conhecido e metadados point-in-time.
- **Dados proibidos:** máxima, mínima, fechamento, volume, eventos, fills ou liquidez de `D+1` ou posterior durante a geração de features e decisão.
- **Normalização:** scaler, imputação, seleção de features e calibração devem ser ajustados somente nas janelas permitidas pelo split temporal.

## 5. Horizonte, lados e classes

- **Horizonte operacional máximo:** 15 pregões após a data de decisão.
- **Lados avaliados:** `BUY` e `SELL`.
- **Classes supervisionadas:** `down`, `neutral`, `up`.
- **Interpretação econômica:** `up` e `down` só são úteis quando convertidos em trades com expectativa líquida positiva após custos e regras reais de entrada/saída; `neutral` representa ausência de vantagem suficiente ou trade não executável.

## 6. Entrada, saída e execução pretendidas

- **Entrada:** ordem limitada a partir de `D+1`, parametrizada por deslocamento de entrada de 2% em relação ao fechamento de `D`.
- **Target inicial:** 7%.
- **Stop inicial:** 7%.
- **Expiração:** marcação a mercado no fim de 15 pregões se target/stop não ocorrerem.
- **Política de ambiguidade inicial:** `conservative_stop_first` quando target e stop forem possíveis no mesmo candle sem evidência intraday suficiente.
- **Motor obrigatório das próximas fases:** `label_eod_barrier_v2`, stateful, compartilhado por labels, backtest, paper e produção.

## 7. Capacidade operacional

- **Execução:** sinais EOD com ordens preparadas para `D+1`.
- **Frequência:** diária, respeitando calendário B3 e feriados.
- **Capacidade inicial:** limitada por liquidez, número máximo de sinais, concentração por ativo/setor e capital ocupado por posições com horizonte de até 15 pregões.
- **Restrição de promoção:** nenhuma liberação automática de capital; shadow e paper são obrigatórios antes de operação controlada.
- **Fallback:** qualquer promoção futura deve manter fonte híbrida e fallback heurístico.

## 8. Custos e cenários de estresse

Os custos devem ser tratados como parte do protocolo, não como ajuste posterior.

| Cenário | Uso | Requisito |
|---|---|---|
| `1.0x` | custo base | superar champion e baselines em research OOS |
| `1.5x` | estresse moderado | manter robustez no Gate Research |
| `2.0x` | estresse severo | obrigatório no locked holdout |

Custos mínimos a modelar nas próximas fases: spread, slippage, taxas, aluguel quando houver venda, restrição de liquidez e diferença entre preço teórico e executável.

## 9. Baseline equivalente e champion

Todo challenger do protocolo deve ser comparado contra:

1. não operar / sempre `neutral`;
2. frequência aleatória equivalente;
3. heurística operacional atual;
4. regressão logística;
5. árvore ou gradient boosting tabular;
6. MLP simples;
7. champion operacional vigente, quando houver.

A comparação principal é econômica e líquida contra o champion. Métricas classificatórias podem diagnosticar comportamento, mas não autorizam avanço de gate.

## 10. Motivo para usar rede neural

A rede neural é permitida nesta hipótese porque o padrão pode depender de interações não lineares entre múltiplas variáveis de preço, volume, regime e liquidez. Ainda assim, ela só avança se demonstrar ganho líquido material, robusto e reproduzível em relação a baselines mais simples. Complexidade, acurácia ou `score_total` isolados não justificam evolução.

## 11. Métrica primária da Fase 0

A métrica primária declarada para seleção futura é:

```text
median_delta_net_expectancy_vs_champion
```

Ela deve ser avaliada por família, fold e seed, com custos descontados e comparação pareada quando os dados estiverem disponíveis. Métricas auxiliares obrigatórias incluem proporção de folds positivos, pior fold, drawdown, trades suficientes, sensibilidade a custos, calibração e complexidade.

## 12. Contrato inicial congelado

```json
{
  "protocol_version": "neural_eod_protocol_v1",
  "hypothesis_id": "eod_barrier_direction_v2",
  "dataset": {
    "feature_version": "feature_eod_tabular_v2",
    "label_version": "label_eod_barrier_v2",
    "universe_version": "b3_point_in_time_v1"
  },
  "execution": {
    "entry_pct": 0.02,
    "target_pct": 0.07,
    "stop_pct": 0.07,
    "horizon_sessions": 15,
    "same_bar_policy": "conservative_stop_first",
    "cost_scenarios": [1.0, 1.5, 2.0]
  },
  "validation": {
    "mode": "nested_expanding_walk_forward",
    "outer_folds": 5,
    "outer_test_sessions": 63,
    "calibration_sessions": 42,
    "embargo_sessions": 15,
    "locked_holdout_sessions": 126
  },
  "selection": {
    "primary_metric": "median_delta_net_expectancy_vs_champion",
    "minimum_positive_folds": 4,
    "seed_repeats": 3,
    "score_is_promotional": false
  },
  "promotion": {
    "requires_explicit_approval": true,
    "initial_signal_source": "hybrid",
    "fallback_signal_source": "heuristic"
  }
}
```

## 13. Checklist de aceite da Fase 0

- [x] Padrão de mercado pretendido declarado.
- [x] Universo point-in-time declarado.
- [x] Instante da decisão declarado.
- [x] Horizonte declarado.
- [x] Lados `BUY` e `SELL` declarados.
- [x] Entrada, target, stop, expiração e política de ambiguidade declarados.
- [x] Capacidade operacional e restrições de promoção declaradas.
- [x] Custos e cenários de estresse declarados.
- [x] Baselines e champion declarados.
- [x] Motivo para usar rede neural declarado.
- [x] Métrica econômica primária declarada.
- [x] Contrato inicial do protocolo registrado.

## 14. Próximo passo autorizado

Com a Fase 0 executada, o próximo trabalho permitido é a Fase 1: implementar o `label_eod_barrier_v2` e o motor de trade stateful único, garantindo paridade entre label, backtest, paper e avaliação operacional antes de novas rodadas de evolução neural.
