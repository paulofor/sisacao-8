# Fase 2 — Sistemas baseline simples

## Objetivo executado

Esta etapa prepara as primeiras estratégias baseline do laboratório quantitativo. O foco é criar hipóteses simples, auditáveis e comparáveis antes de avançar para rankings mais complexos ou modelos de machine learning.

## Artefato criado

- Script BigQuery: `infra/bq/09_quant_phase2_baseline_systems.sql`.

O script cria o catálogo de estratégias baseline, uma camada de features diárias, a view de sinais candidatos e views de status/alertas para alimentar as telas **Estratégias Baseline** e **Detalhe da Estratégia**.

## Estratégias baseline preparadas

| Estratégia | Família | Lado | Hipótese resumida |
|---|---|---|---|
| `baseline_daily_momentum_v1` | Momentum diário | BUY | Força recente com volume relativo elevado tende a continuar no curto prazo. |
| `baseline_daily_mean_reversion_v1` | Reversão à média diária | BUY | Quedas fortes em ativos ainda saudáveis podem reverter parcialmente. |
| `baseline_daily_breakout_v1` | Rompimento diário | BUY | Fechamento acima da máxima recente com volume indica fluxo comprador. |
| `baseline_gap_continuation_v1` | Gap continuation | BUY | Gap positivo confirmado por fechamento forte pode continuar. |
| `baseline_gap_fade_v1` | Gap fade | SELL | Gap positivo excessivo com fechamento fraco pode devolver movimento. |
| `baseline_relative_strength_ranking_v1` | Ranking diário | BUY | Top 5 por força relativa, tendência e volume relativo. |
| `baseline_ibov_regime_filter_v1` | Regime de mercado | BUY/filtro | Filtro para operar comprado somente em ambiente favorável. |

## Componentes técnicos

### `quant_baseline_strategy_config`

Tabela de catálogo com:

- identificadores de estratégia e versão;
- hipótese de mercado;
- regra de entrada e regra de saída;
- horizonte máximo;
- alvo, stop e parâmetros em JSON;
- status operacional inicial.

### `vw_quant_phase2_daily_features`

View de features diárias sobre o universo elegível da Fase 0:

- retornos de 3, 5 e 20 pregões;
- médias móveis de 20 e 50 pregões;
- volume médio e volume relativo;
- máxima/mínima anteriores de 20 pregões;
- RSI aproximado de 14 pregões;
- gap percentual contra o fechamento anterior.

### `vw_quant_phase2_baseline_signal_candidates`

View que converte as regras baseline para o contrato comum da Fase 1:

- `signal_id` determinístico;
- `strategy_id`, família e versão;
- ticker, data do sinal e lado;
- preço esperado de entrada, alvo, stop e horizonte;
- score/ranking quando aplicável;
- metadados JSON com as features que explicam o sinal.

### `vw_quant_phase2_baseline_status`

View para a tela **Estratégias Baseline** com:

- status configurado;
- quantidade de sinais gerados;
- dias com sinais;
- última data sinalizada;
- métricas mais recentes do comparador de estratégias;
- status calculado (`sem_sinais`, `amostra_insuficiente`, `promissora`, `reprovada` ou `em_teste`).

### `vw_quant_phase2_strategy_detail_alerts`

View para alertas automáticos na tela **Detalhe da Estratégia**:

- amostra insuficiente;
- ausência de expectativa líquida positiva;
- profit factor fraco;
- drawdown elevado.

## Decisões de implementação

- As baselines usam um universo de pesquisa derivado da Fase 0: tickers `elegivel` entram diretamente, e tickers em `observacao` só entram quando mantêm cobertura mínima de 90%, volume financeiro suficiente, preços/volumes válidos e no máximo 3 duplicidades técnicas por ticker/data.
- A camada de features deduplica `cotacao_ohlcv_diario` por `ticker`/`data_pregao`, mantendo o registro mais recente por `atualizado_em`/`ingestion_run_id`; isso evita travar a pesquisa por poucas duplicidades de carga sem liberar dados realmente ruins.
- A geração de sinais é feita em views, sem persistir trades automaticamente; a persistência deve acontecer quando o motor comum da Fase 1 processar os candidatos.
- Os parâmetros ficam em JSON para permitir ajustes rápidos sem migração de schema a cada variação.
- O ranking diário limita a seleção ao top 5 por data, em linha com a disciplina operacional já usada em sinais EOD.
- A estratégia de regime foi cadastrada como baseline/filtro para comparação futura, mas não gera trades isolados nesta primeira preparação.

## Critérios de saída atendidos

- As seis famílias baseline iniciais foram parametrizadas.
- Há uma view única de sinais candidatos compatível com o contrato comum de backtest.
- As telas de baseline e detalhe têm fontes de dados propostas para status, métricas e alertas.
- Estratégias sem vantagem poderão permanecer como referência e aparecer como `reprovada` após métricas suficientes.

## Próximos passos

1. Aplicar `infra/bq/09_quant_phase2_baseline_systems.sql` no BigQuery.
2. Inserir os sinais candidatos selecionados em `quant_strategy_signals` para uma janela histórica controlada.
3. Rodar o motor comum da Fase 1 para popular `quant_backtest_trades` e `quant_backtest_metrics`.
4. Expor endpoints backend para `vw_quant_phase2_baseline_status` e `vw_quant_phase2_strategy_detail_alerts`.
5. Criar as telas **Estratégias Baseline** e **Detalhe da Estratégia** no frontend.
