# Sprint 1 — Entrega técnica

Este documento resume as decisões e contratos implementados para a Sprint 1 do projeto **Sisacao-8**, conforme solicitado na especificação `SPEC_SPRINT1_SISACAO8.md`.

## Universo de tickers

- Fonte primária: tabela `cotacao_intraday.acao_bovespa` (coluna `ativo = TRUE`).
- Arquivo de apoio: `functions/get_stock_data/tickers.txt` permite definir conjuntos reduzidos em ambientes locais.
- O job `get_stock_data` reaproveita essa mesma lista tanto para o download da B3 quanto para o scraping intraday e para os relatórios de monitoramento.

## Timezone e formatos

- Todos os timestamps são armazenados em `America/Sao_Paulo` e persistidos como `DATETIME` sem timezone no BigQuery.
- Campos de data utilizam o padrão ISO (`YYYY-MM-DD`).
- As funções expõem o parâmetro `date=YYYY-MM-DD` para reprocessamento idempotente.

## Saída dos sinais (`eod_signals`)

A função `functions/eod_signals` publica um documento JSON seguindo o contrato abaixo e insere os mesmos dados na tabela `cotacao_intraday.sinais_eod`:

```json
{
  "date_ref": "2024-05-06",
  "valid_for": "2024-05-07",
  "model_version": "signals_v0",
  "signals": [
    {
      "ticker": "PETR4",
      "side": "BUY",
      "entry": 32.34,
      "target": 34.60,
      "stop": 30.08,
      "rank": 1,
      "x_rule": "close(D)*0.9800",
      "y_target_pct": 0.07,
      "y_stop_pct": 0.07,
      "model_version": "signals_v0",
      "created_at": "2024-05-06T21:35:00-03:00",
      "source_snapshot": "<sha256>",
      "code_version": "<git-sha>",
      "volume": 15000000,
      "close": 33.0
    }
  ]
}
```

Campos adicionais presentes na tabela BigQuery:

- `date_ref` (DATE), `valid_for` (DATE), `ticker`, `side`, `entry`, `target`, `stop`, `rank`.
- `x_rule`, `y_target_pct`, `y_stop_pct`, `model_version`, `created_at`, `source_snapshot`, `code_version`.
- `volume`, `close` para auditoria e ranking.

## Ambiente e credenciais

- **Projeto padrão**: `ingestaokraken` com região `us-central1`.
- **Dataset**: `cotacao_intraday` (tabelas `cotacao_ohlcv_diario`, `candles_intraday_15m`, `candles_intraday_1h`, `sinais_eod`).
- **Secrets obrigatórios**:
  - `BOT_TOKEN` e `CHAT_ID` (Secret Manager) para a função `alerts`.
- **Contas de serviço**:
  - `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` com as permissões descritas em `docs/configuracoes_scheduler.md` para Cloud Scheduler e Scheduled Queries.

## Versionamento

- `MODEL_VERSION`: `signals_v0` (fixo na Sprint 1, calculado em `functions/eod_signals`).
- `CODE_VERSION`: variável de ambiente opcional lida pela função `eod_signals`. Em produção configure com o `git rev-parse HEAD` do deploy. Em ambiente local assume `local`.
- `source_snapshot`: hash SHA-256 calculado a partir dos candles diários utilizados na geração do dia, garantindo rastreabilidade do dataset de entrada.

## Referências rápidas

- Funções implementadas: `get_stock_data`, `intraday_candles`, `eod_signals`, `alerts`.
- Scripts SQL atualizados: `infra/bq/cotacao_fechamento_diario.sql` (candles) e `infra/bq/signals_oscilacoes.sql` (tabela `sinais_eod`).
- Monitoramento: dashboards e alertas descritos em `docs/monitoramento.md` e `docs/manual_agendamentos_gcp.md`.
