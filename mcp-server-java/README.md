# MCP Server Java (Spring Boot)

Servidor MCP em Java com Maven + Spring Boot, substituindo a versão C++ no deploy da VPS.

## Executar localmente

```bash
cd mcp-server-java
mvn spring-boot:run
```

## Endpoint

- `POST /mcp`

Métodos JSON-RPC suportados:
- `initialize`
- `tools/list`
- `tools/call`

Tools disponíveis (paridade de nomes com a versão Python):
- `ping`
- `runtime_config`
- `bigquery_access_check`
- `bigquery_query`
- `cloud_run_function_logs`
- `cloud_scheduler_job`

## Build container

```bash
docker build -f mcp-server-java/Dockerfile -t sisacao8-mcp-server-java .
```

## Executar container com credencial GCP

Para que a tool `cloud_run_function_logs` funcione, o container precisa ter:
- `gcloud` instalado (já incluído no `Dockerfile`);
- credencial GCP montada no filesystem do container.

Se a chave no host está em `/opt/sisacao/chaves/codex.json`, suba assim:

```bash
docker run -d \
  --name sisacao8-mcp-server-java \
  -p 80:80 \
  -v /opt/sisacao/chaves/codex.json:/opt/sisacao/chaves/codex.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/opt/sisacao/chaves/codex.json \
  -e CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE=/opt/sisacao/chaves/codex.json \
  -e GCP_PROJECT=ingestaokraken \
  ghcr.io/paulofor/sisacao-8/mcp-server-java:latest
```

Valide dentro do container:

```bash
docker exec -it sisacao8-mcp-server-java sh -lc 'which gcloud && gcloud --version'
docker exec -it sisacao8-mcp-server-java sh -lc 'test -r "$GOOGLE_APPLICATION_CREDENTIALS" && echo "credencial ok" || echo "credencial ausente"'
```

## Testes

```bash
cd mcp-server-java
mvn test
```


## Consultar Cloud Scheduler via MCP

A tool `cloud_scheduler_job` executa `gcloud scheduler jobs describe` no runtime autenticado do MCP. Exemplo de chamada JSON-RPC após `initialize`:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "cloud_scheduler_job",
    "arguments": {
      "job_name": "neural-evolution-weekly",
      "location": "us-east1"
    }
  }
}
```
