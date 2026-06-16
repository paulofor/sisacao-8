# Funções Cloud

Cada subdiretório contém uma função ou job HTTP com `main.py` e `requirements.txt` minimalista.

## Funções operacionais atuais

- `get_stock_data`: coleta diária OHLCV da B3 e grava em BigQuery.
- `google_finance_price`: coleta intraday via Google Finance/Cloud Run e grava em BigQuery.
- `intraday_candles`: consolida candles intraday de 15m/1h a partir da tabela bruta.
- `eod_signals`: gera sinais EOD condicionais com parâmetros versionados.
- `backtest_daily`: simula sinais anteriores e atualiza trades/métricas rolling.
- `alerts`: emite alertas/resumos operacionais.
- `dq_checks`: executa checks diários de qualidade de dados e incidentes.
- `quant_daily_evaluation`: materializa a avaliação diária de ranking, robustez e paper trading em `quant_daily_model_evaluation`.
