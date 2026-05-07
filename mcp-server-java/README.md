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

## Build container

```bash
docker build -f mcp-server-java/Dockerfile -t sisacao8-mcp-server-java .
```

## Testes

```bash
cd mcp-server-java
mvn test
```
