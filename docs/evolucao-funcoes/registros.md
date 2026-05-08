
# Registros — Evolução Funções

> Orientação: todos os registros deste documento devem sempre incluir **data e hora no fuso UTC-3**.
> Neste documento segue política de **append-only** (não pode ter nenhuma linha apagada; apenas inserções).

## 2026-05-05 08:35 UTC-3 — MCP Server (logs de execução)

- Ajustada a tool `cloud_run_function_logs` em `mcp-server/src/server.py` para reduzir ruído de auditoria por padrão:
  - novo parâmetro `include_audit_logs` (default `False`);
  - quando `False`, exclui `cloudaudit.googleapis.com/activity` e `cloudaudit.googleapis.com/data_access`.
- Mantida a compatibilidade de nomes com hífen/underscore para localizar logs de runtime com maior precisão.
- Objetivo operacional: priorizar logs de invocação/execução e evitar retorno predominante de eventos administrativos de deploy.

## 2026-05-05 09:05 UTC-3 — Correção `backtest_daily` (serialização JSON)

- Corrigida a persistência no BigQuery da função `backtest_daily` para evitar erro `TypeError: Object of type date is not JSON serializable` durante `load_table_from_json`.
- Implementada normalização de payload antes da carga, convertendo automaticamente campos `datetime.date` e `datetime.datetime` para `ISO-8601` (`YYYY-MM-DD` e timestamp ISO).
- A correção foi aplicada no fluxo genérico de `_load_table`, cobrindo tanto gravação de `backtest_trades` quanto de `backtest_metrics`.

## 2026-05-05 20:10 UTC-3 — Hardening deploy MCP (healthcheck + smoke test)

- Adicionado `HEALTHCHECK` no `mcp-server/Dockerfile` com chamada JSON-RPC para `tools/call` -> `ping` em `http://127.0.0.1:80/mcp`, incluindo `Accept: application/json, text/event-stream`.
- Atualizado `.github/workflows/deploy-mcp-vps.yml` para executar smoke test pós-deploy com tentativas e retry, validando disponibilidade real do endpoint MCP antes de concluir o job.
- Em caso de falha no smoke test, o workflow agora imprime status do container e últimos logs e encerra com erro para evitar deploy verde com serviço indisponível.

## 2026-05-06 09:40 UTC-3 — MCP logs com projeto/região fixos e sem filtros

- Ajustado `mcp-server/src/server.py` para fixar `project=ingestaokraken` e `region=us-east1` no runtime do servidor MCP, garantindo padronização operacional na leitura de logs.
- Removida a montagem de `--log-filter` na chamada `gcloud run services logs read`, mantendo saída sem filtros adicionais de severidade/auditoria.
- Simplificado o filtro no fallback da Cloud Logging API para considerar apenas recurso (Cloud Run/Cloud Function) e janela de tempo.

## 2026-05-07 10:45 UTC-3 — Migração workflow MCP Python -> C++

- Desativado o gatilho de deploy do MCP baseado em alterações de `mcp-server/**` (Python) e ativado o gatilho para `mcp-server-cpp/**`.
- Atualizado o workflow `.github/workflows/deploy-mcp-vps.yml` para build/push/deploy da imagem `mcp-server-cpp`, incluindo uso do novo `mcp-server-cpp/Dockerfile`.
- Ajustados nome e referências do container na VPS para `sisacao8-mcp-server-cpp`, preservando validação de disponibilidade via smoke test do endpoint MCP.
- Ajustados filtros de caminhos em `.github/workflows/ci.yml` e `.github/workflows/deploy.yml` para manter separação entre pipelines de funções/cloud e mudanças exclusivas do MCP.

## 2026-05-07 01:40 UTC-3 — Novo MCP Server Java (Spring Boot)

- Criado o módulo `mcp-server-java` com `Maven` + `Spring Boot 3.3.5` e `Java 21` como base para evolução de um servidor MCP em Java.
- Implementado endpoint `POST /mcp` com suporte inicial aos métodos JSON-RPC `initialize` e `tools/list`, além de retorno de erro para métodos não mapeados.
- Adicionado teste com `MockMvc` validando o fluxo de `initialize` e documentação de execução/testes no `mcp-server-java/README.md`.
- Incluído `.gitignore` local para ignorar artefatos de build (`/target/`).

## 2026-05-07 02:35 UTC-3 — MCP Server Java: conformidade do handshake de sessão

- Ajustado `mcp-server-java/src/main/java/com/sisacao/mcpserver/McpController.java` para seguir o padrão de comunicação MCP via header `mcp-session-id`:
  - `initialize` agora gera `UUID`, registra sessão ativa em memória e devolve `mcp-session-id` no header da resposta;
  - `tools/list` e `tools/call` agora exigem header de sessão válido antes de processar a chamada.
- Adicionado retorno de erro JSON-RPC para cenários de sessão ausente (`-32001`) e sessão inválida (`-32002`), facilitando troubleshooting do cliente.
- Atualizados testes em `mcp-server-java/src/test/java/com/sisacao/mcpserver/McpControllerTest.java` para cobrir:
  - presença do header em `initialize`;
  - sucesso de `tools/list`/`tools/call` com sessão válida;
  - rejeição de `tools/list` sem `mcp-session-id`.

## 2026-05-07 21:45 UTC-3 — MCP Server Java: runtime com gcloud + credencial em container

- Atualizado `mcp-server-java/Dockerfile` para instalar `google-cloud-cli` no estágio de runtime, incluindo repositório oficial Google apt e limpeza de cache (`/var/lib/apt/lists`).
- Definido `GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/google/codex.json` no runtime do container para padronizar o caminho da service account usada pelas tools que consultam GCP.
- Atualizado `mcp-server-java/README.md` com instruções operacionais de `docker run` montando a chave do host (`/opt/sisacao/chaves/codex.json`) para o caminho interno esperado no container.
- Incluídos comandos de validação pós-subida para confirmar presença do `gcloud` e legibilidade da credencial dentro do container.
