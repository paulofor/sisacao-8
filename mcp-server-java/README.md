# MCP Server Java (Spring Boot)

Servidor MCP inicial em Java com Maven + Spring Boot.

## Executar localmente

```bash
cd mcp-server-java
./mvnw spring-boot:run
```

Ou, se preferir usar Maven instalado no sistema:

```bash
cd mcp-server-java
mvn spring-boot:run
```

## Endpoint

- `POST /mcp`

Métodos JSON-RPC suportados no bootstrap inicial:
- `initialize`
- `tools/list`

## Testes

```bash
cd mcp-server-java
mvn test
```
