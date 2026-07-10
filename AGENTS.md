**Todo trabalho realizado nesse projeto deve ser registrado em : /docs/diario/registros2.md**
**O próximo passo operacional das redes neurais deve ser mantido em: /docs/diario/proximo-passo-redes2.md. Sempre que o ponto de parada ou próximo passo das redes mudar, atualize esse arquivo além do diário principal.**

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

## 1.1. Investigação e resolução de causas prováveis
- Sempre que identificar uma possível causa para um problema operacional, bug, falha de deploy, erro de dados ou comportamento inesperado, use as ferramentas disponíveis no ambiente para confirmar a hipótese antes de tratá-la como conclusão.
- Quando a hipótese for confirmada, resolva o problema no mesmo fluxo de trabalho sempre que a correção estiver dentro do escopo e das permissões disponíveis.
- Registre no diário do projeto quais ferramentas/comandos foram usados para confirmar a causa e qual correção foi aplicada.

## 2. Convenções de código
- **Formatação:** `black` + `isort`
- **Lint:** `flake8` com `flake8-bugbear`
- **Typing:** `mypy`
- **Antes de abrir PR:** executar obrigatoriamente os testes e checks locais (`flake8` e `pytest`) e só abrir PR com tudo passando.
- **Estrutura de futuras funções:** cada função residirá em `functions/<nome_da_funcao>/` com `main.py` e `requirements.txt` minimalista.
- **Screenshots:** não gerar nem versionar screenshots/evidências visuais para alterações de frontend, salvo quando o usuário pedir explicitamente.

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

### REGRA OBRIGATÓRIA (MCP)

- **SEMPRE** acessar o MCP Server via **JSON-RPC**.
- **SEMPRE** conectar usando **HTTP**: `http://mcpserversisacao.shop/mcp`.
- **NUNCA** usar **HTTPS** para este endpoint MCP.
- Em qualquer automação/script/comando, trate uso de `https://mcpserversisacao.shop/mcp` como configuração inválida.

### Como acessar corretamente (passo a passo obrigatório)

1. Envie `initialize` por **HTTP POST** para `http://mcpserversisacao.shop/mcp` com headers:
   - `Content-Type: application/json`
   - `Accept: application/json, text/event-stream`
2. Capture o header de resposta `mcp-session-id`.
3. Para qualquer chamada seguinte (`tools/list`, `tools/call`, etc.), reenvie:
   - os mesmos headers de `Content-Type` e `Accept`;
   - o header `mcp-session-id: <valor_da_sessao>`.
4. Se houver `503`/timeout, aplicar retry com backoff e repetir o fluxo mantendo a regra de **HTTP** (sem HTTPS).

Exemplo mínimo com `curl`:

```bash
# 1) initialize
curl -sS -D - -X POST 'http://mcpserversisacao.shop/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"codex-cli","version":"1.0"}}}'

# 2) tools/list (substituir <MCP_SESSION_ID>)
curl -sS -D - -X POST 'http://mcpserversisacao.shop/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <MCP_SESSION_ID>' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

### Cloud Scheduler e OIDC — cuidado operacional obrigatório

- Antes de sugerir `gcloud scheduler jobs update/create http` com `--oidc-service-account-email`, confirme se o job atual usa OIDC e se a service account existe.
- Para jobs que chamam Cloud Functions públicas (`--allow-unauthenticated`), prefira comandos **sem OIDC**. Só inclua OIDC quando houver decisão explícita de proteger a invocação.
- Se usar OIDC, valide previamente:
  1. `gcloud iam service-accounts describe sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com --project=ingestaokraken`;
  2. a service account possui `roles/run.invoker` no serviço/função Gen2 alvo;
  3. a conta que executa o `gcloud scheduler jobs create/update http` possui `roles/iam.serviceAccountUser` sobre essa service account;
  4. a conta também possui permissão de Scheduler, por exemplo `roles/cloudscheduler.admin` ou permissão equivalente para `cloudscheduler.jobs.create/update`.
- Se `gcloud scheduler jobs update http` retornar `NOT_FOUND`, não concluir de imediato que o job não existe: primeiro executar `gcloud scheduler jobs describe <job> --project=ingestaokraken --location=us-east1` e verificar projeto, location, conta ativa e permissões. Em GCP, falta de permissão ou service account OIDC inválida pode aparecer como `NOT_FOUND`/`PERMISSION_DENIED`.
- No caso validado do `neural-evolution-daily`, o job existe em `ingestaokraken/us-east1` e estava sem OIDC no diagnóstico; portanto o update recomendado enquanto a função estiver pública é sem `--oidc-service-account-email` e sem `--oidc-token-audience`.

### Dicas operacionais validadas para usar o MCP

- O endpoint pode retornar `503`/timeout enquanto o upstream do MCP Java não está saudável. Nesses casos, **não trocar para HTTPS**: aguarde alguns instantes, repita `initialize` por HTTP e capture um novo `mcp-session-id`.
- Depois do `initialize`, não basta chamar ferramentas sem sessão: todas as chamadas `tools/list` e `tools/call` precisam reenviar o header `mcp-session-id`.
- Para consultar logs da Cloud Function Gen2 via MCP, use `tools/call` com a ferramenta `cloud_run_function_logs` e o argumento **`function_name`**. Os argumentos `function` ou `service` não foram aceitos pelo MCP e retornaram `function_name vazio`.
- Para reduzir timeouts ao consultar logs, prefira janelas curtas e limite moderado, por exemplo:

```bash
curl -sS -X POST 'http://mcpserversisacao.shop/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <MCP_SESSION_ID>' \
  --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cloud_run_function_logs","arguments":{"function_name":"neural_training_dataset","hours":1,"limit":120}}}'
```

- Para validar schemas no BigQuery via MCP, use `tools/call` com `bigquery_query` e consultas read-only em `INFORMATION_SCHEMA`, por exemplo:

```bash
curl -sS -X POST 'http://mcpserversisacao.shop/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <MCP_SESSION_ID>' \
  --data '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"bigquery_query","arguments":{"query":"SELECT column_name, data_type FROM `ingestaokraken.cotacao_intraday.INFORMATION_SCHEMA.COLUMNS` WHERE table_name='\''feriados_b3'\'' ORDER BY ordinal_position","limit":50}}}'
```

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
