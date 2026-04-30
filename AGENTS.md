

## Descrição dos principais arquivos e pastas

* **AGENTS.md**: Arquivo dedicado a fornecer contexto e diretrizes ao OpenAI Codex (ou outros agentes de IA) sobre o domínio do projeto, convenções de código, dependências externas e tarefas pendentes. **Não descreve nenhuma função ainda**.
* **.github/workflows/**: CI/CD – o *ci.yml* executa lint (`flake8`), formatação (`black`) e testes (`pytest`). O *deploy.yml* continua como placeholder, sem deploy de funções.
* **requirements.txt**: Lista de pacotes de desenvolvimento compartilhados.
* **functions/**: Diretório reservado; permanece vazio até que decidamos criar a primeira Cloud Function.

---


# Codex Agents Guide – sisacao‑8

Este arquivo fornece contexto a agentes de IA (OpenAI Codex, ChatGPT, etc.) sobre este repositório.

## 1. Visão geral do projeto
- **Objetivo:** Coletar cotações de ações em tempo quase‑real e armazená‑las no BigQuery para análises posteriores.
- **Estado atual:** Primeira Cloud Function implementada (`get_stock_data`).
- **Próximo marco:** Evoluir o processo de coleta e documentar novas funções.

## 2. Convenções de código
- **Formatação:** `black` + `isort`
- **Lint:** `flake8` com `flake8-bugbear`
- **Typing:** `mypy`
- **Antes de abrir PR:** executar obrigatoriamente os testes e checks locais (`flake8` e `pytest`) e só abrir PR com tudo passando.
- **Estrutura de futuras funções:** cada função residirá em `functions/<nome_da_funcao>/` com `main.py` e `requirements.txt` minimalista.

## 3. Dependências externas aprovadas (para uso futuro)
| Pacote | Uso | Observação |
|--------|-----|-----------|
| `yfinance` | Download de cotações | Substituível por AlphaVantage ou IEX se necessário. |
| `google-cloud-bigquery` | Inserção de dados | Versão `>=3.12`. |
| `functions-framework` | Testes locais | Dev only. |

## 4. Variáveis de ambiente essenciais (pré‑definidas)
- `BQ_TABLE` → `ingestaokraken.cotacao_intraday.candles_diarios`
- Tabela intraday utilizada pelas funções `google_finance_price` e monitoramentos derivados:
  `ingestaokraken.cotacao_intraday.cotacao_bovespa`
- `GCP_PROJECT` → `ingestaokraken`
- `GCP_REGION` → `us-east1`

---
> **Importante:** Novas funções devem seguir o padrão deste repositório. Mantenha o guia atualizado a cada adição.

--

## Serviços em execução

- **Backend web** e **frontend web** estão publicados na VPS em execução no endereço: <http://34.194.252.70/>.

---

## Princípios de arquitetura da plataforma

**Servidor MCP** : Chame o endpoint MCP http://mcpserversisacao.shop/mcp via JSON-RPC. Quando precisar analisar casos específicos acesse o BigQuery.

1. **Backend Java + BigQuery**: Um serviço REST (Spring Boot ou Quarkus) fornecerá APIs para consultar sinais, parâmetros e execuções de treinamento diretamente das tabelas no BigQuery, aplicando camadas de serviço/repositório para encapsular o acesso aos dados.
2. **Frontend web moderno**: Uma aplicação single-page (React ou Vue) consumirá as APIs expostas pelo backend para construir dashboards ricos com controles de sinais, acompanhamento de jobs de treinamento e ajustes de parâmetros.
3. **Integração desacoplada**: Comunicação exclusiva via HTTP/JSON (ou WebSockets quando necessário), com autenticação unificada (OAuth2/OpenID) e versionamento de endpoints para facilitar evoluções independentes entre frontend e backend.
4. **Observabilidade e governança**: Logs estruturados, métricas e rastreamento distribuído devem ser configurados desde o início para acompanhar pipelines de dados, execuções de ML e interações dos usuários.
5. **Infraestrutura GCP**: O projeto reutiliza as variáveis `GCP_PROJECT`, `BQ_TABLE` e `GCP_REGION`, além de service accounts dedicadas para executar consultas e jobs de BigQuery com mínimo privilégio.

---

> As funções serão adicionadas somente após a etapa de planejamento. Por enquanto, concentre‑se em configurar ambiente, CI e documentação.


## 5. Tabelas BigQuery mapeadas nas Functions e objetivos

> Mapeamento extraído dos `main.py` em `functions/` para facilitar operação e troubleshooting.

- `cotacao_intraday.cotacao_b3` (`BQ_INTRADAY_RAW_TABLE`): cotações intraday brutas coletadas em tempo quase real.
- `cotacao_intraday.cotacao_ohlcv_diario` (`BQ_DAILY_TABLE`): candles diários consolidados (OHLCV) por ticker.
- `cotacao_intraday.cotacao_bovespa`: tabela intraday já utilizada por monitoramentos/consultas operacionais.
- `cotacao_intraday.acao_bovespa` (`BQ_TICKERS_TABLE`): universo de tickers ativos/inativos.
- `cotacao_intraday.feriados_b3` (`BQ_HOLIDAYS_TABLE`): calendário de feriados para lógica de pregão.
- `cotacao_intraday.candles_intraday_15m` (`BQ_INTRADAY_15M_TABLE`): agregação intraday em 15 minutos.
- `cotacao_intraday.candles_intraday_1h` (`BQ_INTRADAY_1H_TABLE`): agregação intraday em 1 hora.
- `cotacao_intraday.sinais_eod` (`BQ_SIGNALS_TABLE`): sinais de fim de dia (BUY/SELL) para execução/monitoramento.
- `cotacao_intraday.backtest_trades` (`BQ_BACKTEST_TRADES_TABLE`): operações simuladas do backtest diário.
- `cotacao_intraday.backtest_metrics` (`BQ_BACKTEST_METRICS_TABLE`): métricas agregadas do backtest.
- `cotacao_intraday.dq_checks_daily` (`BQ_DQ_CHECKS_TABLE`): resultados diários dos checks de qualidade.
- `cotacao_intraday.dq_incidents` (`BQ_DQ_INCIDENTS_TABLE`): incidentes detectados nos checks de qualidade.
- `cotacao_intraday.pipeline_config` (`PIPELINE_CONFIG_TABLE`): parâmetros operacionais do pipeline.
- `cotacao_intraday.strategy_config` (`BQ_STRATEGY_CONFIG_TABLE`): parâmetros/versionamento da estratégia de sinais.

Objetivo operacional resumido:
1. Coletar cotações (intraday + diário).
2. Gerar sinais EOD com rastreabilidade de configuração.
3. Rodar backtests e consolidar métricas.
4. Executar DQ checks e registrar incidentes.
5. Expor dados confiáveis para backend/frontend e observabilidade.
