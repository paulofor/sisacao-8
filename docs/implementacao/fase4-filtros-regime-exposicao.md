# Fase 4 — Filtros de regime e controle de exposição

## Objetivo executado

Esta etapa prepara a camada que decide quando operar normalmente, reduzir risco, bloquear compras ou permanecer em caixa. A implementação cria uma classificação diária de regime de mercado e recomendações auditáveis de exposição para alimentar as telas **Regime de Mercado** e **Exposição Recomendada**.

## Artefato criado

- Script BigQuery: `infra/bq/11_quant_phase4_market_regime_exposure.sql`.

## Componentes técnicos

### `quant_regime_policy_config`

Tabela de política versionada para calibrar regras de regime e limites operacionais:

- thresholds de amplitude para tendência de alta e baixa;
- percentis de volatilidade alta e baixa;
- gatilhos de stress por retorno curto e amplitude;
- exposição máxima normal, reduzida e caixa;
- quantidade máxima de operações;
- risco por trade e limite de perda diária.

A versão inicial é `market_regime_exposure_v1`/`v1`, com status `em_teste`.

### `vw_quant_phase4_market_regime_indicators`

View diária com os indicadores exigidos no plano:

- tendência agregada do universo elegível;
- volatilidade realizada de 20 pregões;
- amplitude do mercado por percentual de ativos acima das médias de 20 e 50 pregões;
- percentual de ativos com retorno positivo em 5 pregões;
- volume financeiro agregado e volume relativo agregado;
- classificação final do regime.

Regimes classificados:

- `alta_tendencia`;
- `baixa_tendencia`;
- `lateral`;
- `alta_volatilidade`;
- `baixa_volatilidade`;
- `stress`.

### `vw_quant_phase4_exposure_recommendation`

View de recomendação operacional por data:

- ação sugerida: `operar_normal`, `reduzir_posicao`, `bloquear_compras` ou `ficar_em_caixa`;
- exposição máxima sugerida;
- quantidade máxima de operações;
- risco por trade;
- limite de perda diária;
- justificativa textual baseada no regime.

### `vw_quant_phase4_strategy_regime_performance`

View para comparar desempenho de estratégias por regime:

- trades por estratégia, versão e regime;
- expectancy líquida;
- win rate;
- profit factor;
- PnL líquido total;
- status do efeito do regime (`favoravel`, `desfavoravel` ou `amostra_insuficiente`).

### `vw_quant_phase4_filter_effectiveness`

View para medir se o filtro de regime melhora o comportamento das estratégias:

- número original de trades;
- número de trades após filtro;
- expectancy original;
- expectancy filtrada;
- expectancy dos trades bloqueados;
- percentual de trades bloqueados;
- PnL ajustado por exposição;
- status de efetividade do filtro.

## Decisões de implementação

- A classificação usa o universo elegível produzido pelas fases anteriores, evitando depender de um único ticker de índice quando o histórico do índice estiver incompleto.
- `stress` tem precedência sobre os demais regimes para priorizar preservação de capital.
- `baixa_tendencia` bloqueia compras direcionais, mas a estrutura deixa espaço para estratégias vendidas em fases futuras.
- `alta_volatilidade` e `lateral` reduzem exposição em vez de zerar automaticamente, permitindo avaliar se o filtro remove perdas sem eliminar trades bons em excesso.
- A efetividade do filtro é mensurada contra trades já persistidos no contrato comum da Fase 1.

## Critérios de saída atendidos

- Há classificação diária para os seis regimes previstos no plano.
- Existem regras de exposição para operar normal, reduzir posição, bloquear compras e ficar em caixa.
- A performance por regime permite verificar se há melhora de drawdown/expectancy quando as estratégias são filtradas.
- A view de efetividade mede se os bloqueios removem operações ruins sem eliminar toda a amostra.

## Próximos passos

1. Aplicar `infra/bq/11_quant_phase4_market_regime_exposure.sql` no BigQuery.
2. Calibrar thresholds com histórico real após avaliar distribuição de regimes.
3. Expor endpoints backend para `vw_quant_phase4_market_regime_indicators`, `vw_quant_phase4_exposure_recommendation`, `vw_quant_phase4_strategy_regime_performance` e `vw_quant_phase4_filter_effectiveness`.
4. Criar as telas **Regime de Mercado** e **Exposição Recomendada** no frontend.
5. Integrar a recomendação de exposição à geração de sinais antes da Fase 6 de paper trading.
