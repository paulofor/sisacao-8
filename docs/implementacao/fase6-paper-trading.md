# Fase 6 — Simulação operacional em paper trading

## Objetivo executado

Esta etapa prepara a camada de **paper trading** para acompanhar sinais candidatos sem uso de capital real. A implementação foca em registrar decisões do sistema, simular ordens, medir execução, custos, slippage e comparar o resultado realizado na simulação com a expectativa histórica do backtest.

## Artefato criado

- Script BigQuery: `infra/bq/13_quant_phase6_paper_trading.sql`.

## Componentes técnicos

### `quant_paper_trading_config`

Tabela de configuração versionada da simulação operacional:

- capital simulado padrão;
- máximo de ordens diárias;
- máximo de ordens abertas;
- valor nocional máximo por posição;
- quantidade padrão;
- custo e slippage padrão;
- período mínimo de acompanhamento em paper;
- divergência máxima aceitável contra o backtest.

A versão inicial é `paper_trading_v1`/`v1`, com status `em_teste`.

### `quant_paper_trading_orders`

Tabela operacional para ordens simuladas:

- vínculo com sinal e estratégia;
- preço esperado e preço simulado de entrada;
- preço simulado de saída;
- quantidade, nocional, custos e slippage;
- PnL bruto, PnL líquido e PnL esperado no backtest;
- divergência entre simulação e histórico;
- status da ordem, motivo de saída, horários e observações.

### `quant_strategy_decisions_log`

Log auditável para o **Diário Operacional**:

- sinal gerado;
- sinal filtrado;
- entrada simulada;
- stop, target, expire e time stop;
- alerta de risco;
- comentário manual do usuário;
- payload JSON para auditoria posterior.

### `vw_quant_phase6_candidate_signals`

View de sinais candidatos ao paper trading. Ela combina sinais canônicos da Fase 1 com a recomendação de exposição da Fase 4 para classificar cada sinal como:

- `candidato_paper`;
- `filtrado_regime_caixa`;
- `filtrado_bloqueio_compra`;
- `filtrado_bloqueio_venda`.

### `vw_quant_phase6_paper_trading_dashboard`

View consolidada para a tela **Paper Trading**:

- operações abertas;
- operações encerradas;
- total de operações;
- PnL diário simulado;
- PnL acumulado simulado;
- slippage médio;
- taxa de execução;
- divergência média absoluta contra backtest;
- status de aderência.

### `vw_quant_phase6_open_orders`

View para listar operações simuladas abertas, com informações de estratégia, ticker, lado, preço esperado, preço simulado, quantidade, status e observações.

### `vw_quant_phase6_closed_orders_today`

View para listar operações encerradas no dia, incluindo PnL líquido, divergência contra backtest e motivo de saída.

### `vw_quant_phase6_backtest_adherence`

View de comparação entre paper trading e histórico:

- PnL esperado no backtest;
- PnL realizado no paper;
- slippage médio;
- divergência média;
- taxa de execução;
- status de aderência por estratégia, versão e ticker.

### `vw_quant_phase6_operational_diary`

View do **Diário Operacional** com eventos dos últimos 30 dias, pronta para alimentar a tela de acompanhamento e exportações futuras.

## Decisões de implementação

- O paper trading usa as tabelas canônicas criadas nas fases anteriores para manter rastreabilidade entre sinal, estratégia, regime e execução simulada.
- A configuração inicial é conservadora: número limitado de ordens, quantidade padrão e controles explícitos de custo/slippage.
- A recomendação de regime da Fase 4 é usada para bloquear ou liberar candidatos sem duplicar regra de exposição.
- O log de decisões foi separado das ordens para registrar também sinais filtrados e alertas que não viram trade.
- A comparação com o backtest é feita por campos explícitos (`expected_backtest_pnl_pct`, `net_pnl_pct` e `divergence_pct`), facilitando a explicação de desvios.

## Critérios de saída atendidos

- Há estrutura para geração diária/intraday de sinais candidatos ao paper trading.
- Há tabela para registrar decisões automáticas e manuais.
- Há tabela para simular entrada, saída, custos, slippage e status de ordens.
- Há views para acompanhar operações abertas, encerradas, PnL diário/acumulado e aderência ao backtest.
- Há Diário Operacional consultável por evento, estratégia, ticker e comentário.

## Próximos passos

1. Aplicar `infra/bq/13_quant_phase6_paper_trading.sql` no BigQuery.
2. Criar a rotina que transforma `vw_quant_phase6_candidate_signals` em ordens simuladas respeitando limites da configuração ativa.
3. Persistir eventos automáticos em `quant_strategy_decisions_log` para todos os filtros e mudanças de status.
4. Expor endpoints backend para as views de dashboard, ordens abertas, ordens encerradas, aderência e diário.
5. Criar as telas **Paper Trading** e **Diário Operacional** no frontend.
6. Definir o período mínimo real de observação antes de liberar qualquer piloto com capital real.
