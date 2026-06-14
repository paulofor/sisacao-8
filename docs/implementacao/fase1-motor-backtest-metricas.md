# Fase 1 — Motor comum de backtest e métricas

## Objetivo executado

Esta etapa prepara o contrato comum para pesquisa, backtest, comparação e monitoramento dos novos sistemas quantitativos. O foco é impedir que cada estratégia crie sua própria semântica de sinal, trade, custos ou métrica.

## Artefato criado

- Script BigQuery: `infra/bq/08_quant_phase1_backtest_engine.sql`.

O script define três tabelas canônicas e três views operacionais para alimentar as telas **Laboratório de Backtests** e **Comparador de Estratégias**.

## Contratos padronizados

### Sinais de estratégia — `quant_strategy_signals`

Modelo único de entrada de estratégia com:

- identificadores de estratégia (`strategy_id`, `strategy_family`, `strategy_version`, `config_version`);
- ativo, lado, data/hora do sinal e data de referência;
- preço esperado de entrada;
- alvo, stop, regra de saída e horizonte máximo;
- granularidade do candle;
- score de ranking e metadados livres em JSON.

### Trades simulados — `quant_backtest_trades`

Modelo único de trade com:

- vínculo explícito ao sinal (`signal_id`);
- entrada esperada e entrada preenchida;
- saída, PnL bruto, PnL líquido, custo estimado e slippage;
- outcome e motivo de saída;
- duração em barras e dias;
- MFE/MAE;
- regime de mercado e `run_id` para rastreabilidade.

### Métricas consolidadas — `quant_backtest_metrics`

Modelo único de métricas por estratégia, versão, período, ticker, lado e regime com:

- sinais e trades;
- win rate;
- payoff médio;
- expectancy líquida;
- retorno bruto e líquido;
- profit factor;
- max drawdown;
- Sharpe/Sortino;
- score de robustez.

## Views para as telas

### `vw_quant_backtest_lab_trades`

View de detalhe para a tabela paginada de trades da tela **Laboratório de Backtests**.

### `vw_quant_backtest_lab_summary`

View agregada para os cards principais do laboratório:

- número de sinais;
- número de trades;
- win rate;
- payoff médio;
- expectancy líquida;
- profit factor;
- duração média.

### `vw_quant_strategy_comparator`

View para comparação entre estratégias e versões, já com `comparison_status` inicial:

- `amostra_insuficiente`;
- `sem_expectativa_positiva`;
- `profit_factor_fraco`;
- `drawdown_elevado`;
- `comparavel`.

## Decisões de implementação

- Os custos e o slippage são campos obrigatórios em `quant_backtest_trades`; uma simulação sem custo explícito deve gravar zero conscientemente, nunca omitir o valor.
- As tabelas são particionadas por data e clusterizadas por estratégia/ticker para suportar consultas incrementais nas telas.
- O schema separa `strategy_id` de `strategy_version` para permitir comparar hipóteses estáveis com versões diferentes de parâmetros ou código.
- `metadata_json` fica disponível para experimentos sem forçar alteração de schema a cada nova hipótese.
- `run_id` permite auditar reprocessamentos e reproduzir resultados de uma execução específica.

## Critérios de saída atendidos

- Qualquer nova estratégia passa a ter contrato comum de sinal.
- Trades simulados têm custos e slippage explícitos.
- Métricas comparáveis entre estratégias foram padronizadas.
- As views necessárias para laboratório e comparador foram definidas.

## Próximos passos

1. Aplicar `infra/bq/08_quant_phase1_backtest_engine.sql` no BigQuery.
2. Adaptar o motor Python atual para gravar também nas tabelas `quant_*`.
3. Expor endpoints backend para as views `vw_quant_backtest_lab_*` e `vw_quant_strategy_comparator`.
4. Criar as telas do frontend descritas no plano da Fase 1.
