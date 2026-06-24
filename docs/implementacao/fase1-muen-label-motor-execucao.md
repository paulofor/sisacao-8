# Fase 1 MUEN v1 — Label e motor de execução únicos

**Status:** executada em 2026-06-24  
**Protocolo:** `neural_eod_protocol_v1`  
**Label:** `label_eod_barrier_v2`  
**Política de execução:** `execution_eod_barrier_v2_conservative_daily`

## Objetivo

Unificar a lógica de labels neurais EOD e backtest diário em um motor stateful único, evitando que o label encerre a operação no candle de entrada quando target/stop ainda não foram atingidos.

## Implementação

- Criado `sisacao8.trade_engine.simulate_eod_barrier_trade` como motor determinístico compartilhado.
- O ciclo de vida passa a registrar transições entre `PENDING_ENTRY`, `OPEN`, `TARGET`, `STOP`, `EXPIRED_MARK_TO_MARKET`, `EXPIRED_UNFILLED`, `INVALID` e `NO_DATA`.
- `sisacao8.neural_dataset` passa a gerar `label_eod_barrier_v2` usando o motor stateful para BUY e SELL.
- `sisacao8.backtest` passa a delegar a simulação de sinais ao mesmo motor, mantendo a nomenclatura legada de saída (`NO_FILL` e `EXPIRE`) para compatibilidade externa.
- As cópias embarcadas das Cloud Functions `neural_training_dataset` e `backtest_daily` foram sincronizadas para reduzir divergência de deploy.

## Política operacional v2

- Entrada calculada a partir do fechamento de D e buscada apenas nas barras futuras.
- Após fill, a posição permanece aberta até target, stop ou fim do horizonte.
- Empates target/stop em candle diário seguem política conservadora: stop primeiro.
- Expiração após fill marca a mercado pelo fechamento do último candle do horizonte.
- Custos, spread, slippage e aluguel são parâmetros versionados do motor, com default zero para preservar compatibilidade inicial.

## Saídas adicionadas ao dataset

Além dos campos legados (`buy_net_return`, `sell_net_return`, `entry_filled_buy`, `entry_filled_sell`, `days_to_event_*`), o dataset passa a expor a decisão selecionada:

- `trade_side`
- `entry_filled`
- `entry_date`, `entry_price`
- `exit_date`, `exit_price`, `exit_reason`
- `gross_return`, `net_return`
- `holding_sessions`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `execution_policy_version`

## Validação local

- `python -m pytest tests/test_neural_dataset.py tests/test_backtest_engine.py -q`
- O novo teste `test_label_v2_keeps_trade_open_after_entry_until_later_target` confirma que o label não encerra no candle de fill e mantém a posição até target posterior.
