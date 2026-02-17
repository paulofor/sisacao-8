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

A função `functions/eod_signals` publica um documento JSON seguindo o contrato abaixo e insere os mesmos dados na tabela `cotacao_intraday.signals_eod_v0`:

```json
{
  "date_ref": "2024-05-06",
  "valid_for": "2024-05-07",
  "model_version": "X_rule_v0",
  "signals": [
    {
      "ticker": "PETR4",
      "side": "BUY",
      "entry": 32.34,
      "target": 34.60,
      "stop": 30.08,
      "rank": 1,
      "reason": "close(D) * 0.98",
      "model_version": "X_rule_v0",
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

- `reference_date` (DATE), `valid_for` (DATE), `ticker`, `side`, `entry`, `target`, `stop`, `rank`.
- `reason`, `model_version`, `created_at`, `source_snapshot`, `code_version`.
- `volume`, `close` para auditoria e ranking.

## Ambiente e credenciais

- **Projeto padrão**: `ingestaokraken` com região `us-central1`.
- **Dataset**: `cotacao_intraday` (tabelas `candles_diarios`, `candles_intraday_15m`, `candles_intraday_1h`, `signals_eod_v0`).
- **Secrets obrigatórios**:
  - `BOT_TOKEN` e `CHAT_ID` (Secret Manager) para a função `alerts`.
- **Contas de serviço**:
  - `agendamentos-sisacao@<projeto>.iam.gserviceaccount.com` com as permissões descritas em `docs/configuracoes_scheduler.md` para Cloud Scheduler e Scheduled Queries.

## Versionamento

- `MODEL_VERSION`: `X_rule_v0` (fixo na Sprint 1, calculado em `functions/eod_signals`).
- `CODE_VERSION`: variável de ambiente opcional lida pela função `eod_signals`. Em produção configure com o `git rev-parse HEAD` do deploy. Em ambiente local assume `local`.
- `source_snapshot`: hash SHA-256 calculado a partir dos candles diários utilizados na geração do dia, garantindo rastreabilidade do dataset de entrada.

## Referências rápidas

- Funções implementadas: `get_stock_data`, `intraday_candles`, `eod_signals`, `alerts`.
- Scripts SQL atualizados: `infra/bq/cotacao_fechamento_diario.sql` (candles) e `infra/bq/signals_oscilacoes.sql` (tabela `signals_eod_v0`).
- Monitoramento: dashboards e alertas descritos em `docs/monitoramento.md` e `docs/manual_agendamentos_gcp.md`.
