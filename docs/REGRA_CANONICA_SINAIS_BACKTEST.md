# Regra Canônica — Sinais EOD e Execução de Backtest (v1)

## Objetivo
Definir, de forma única, a regra oficial para transformar sinais de fim de dia (EOD) em trades simulados no backtest.

## Linha do tempo (D -> D+1)
1. No fechamento do pregão **D** (ex.: dia 10), o pipeline processa os dados e gera sinais com `date_ref = D`.
2. Cada sinal é marcado para o próximo pregão com `valid_for = D+1` (ex.: dia 11).
3. A execução do sinal deve ser avaliada **somente no pregão D+1**.

## Regra de entrada (canônica)
A entrada é um preço condicional calculado sobre o fechamento de **D**:

- **BUY**: `entry = close(D) * (1 - x_pct)`
- **SELL**: `entry = close(D) * (1 + x_pct)`

> Observação importante: para SELL, a regra canônica é gatilho acima do fechamento (alta), não queda.

### Valor de `x_pct`
- Para esta regra canônica v1, adotar **x_pct = 0.02 (2%)**.
- Assim, os gatilhos de entrada ficam:
  - BUY: queda de 2% sobre `close(D)`;
  - SELL: alta de 2% sobre `close(D)`.

## Regra de validade do sinal
- Se o preço de entrada **não for tocado em D+1**, o sinal deve ser marcado como **NO_FILL** e **descartado no mesmo dia**.
- O sinal **não** deve continuar elegível em D+2, D+3, etc.
- No fechamento de D+1, um novo ciclo gera sinais para D+2 e assim sucessivamente.

## Regra de saída (apenas para sinais preenchidos em D+1)
Para sinais que entraram em D+1:
- Avaliar `TARGET` e `STOP` conforme parametrização da estratégia.
- Se houver manutenção de posição além de D+1, isso deve estar explicitamente configurado e documentado por versão de estratégia.

## Divergência identificada no comportamento atual
O comportamento atualmente implementado no backtest permite tentar entrada por múltiplos pregões (`horizon_days`), iniciando em `valid_for` e mantendo o sinal vivo até preencher ou expirar. Isso diverge desta regra canônica v1.

## Exemplo (didático)
- Dia 10: fecha o mercado, gera sinal com `date_ref=10` e `valid_for=11`.
- Dia 11:
  - se tocar `entry`, entra operação;
  - se não tocar, `NO_FILL` e descarta.
- Dia 11 à noite: gera novos sinais para o dia 12.

## Status
Este documento define a regra canônica de negócio e deve ser usado como referência para ajustes em backend, functions e frontend.
