# AGENTS.md — mcp-server-java

Escopo: este arquivo se aplica a todo o diretório `mcp-server-java/`.

## Objetivo operacional
- O serviço MCP Java expõe `POST /mcp` com JSON-RPC.
- Ferramentas como `cloud_run_function_logs` dependem de autenticação GCP funcional no runtime.

## Regra obrigatória de autenticação GCP
- O container **deve** receber a chave JSON via volume read-only.
- Caminho padrão no container: `/var/secrets/google/codex.json`.
- Variáveis recomendadas:
  - `GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/google/codex.json`
  - `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE=/var/secrets/google/codex.json`
  - `GCP_PROJECT=ingestaokraken` (ou via ambiente do deploy)

## Boot do container
- O entrypoint (`docker-entrypoint.sh`) deve:
  1. validar se `GOOGLE_APPLICATION_CREDENTIALS` existe e é legível;
  2. executar `gcloud auth activate-service-account --key-file=<json>`;
  3. aplicar `gcloud config set project "$GCP_PROJECT"` quando disponível;
  4. iniciar a aplicação Java.

## Troubleshooting rápido
- Verificar credencial no container:
  - `test -r "$GOOGLE_APPLICATION_CREDENTIALS"`
- Verificar conta ativa:
  - `gcloud auth list`
- Verificar projeto:
  - `gcloud config list project`

## Convenções de alteração
- Alterações de deploy devem manter compatibilidade com o workflow `deploy-mcp-java-vps.yml`.
- Evitar hardcode de credencial fora dos paths padrão acima.
