package com.sisacao.mcpserver;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/mcp")
@Validated
public class McpController {

    @Value("${GCP_PROJECT:ingestaokraken}")
    private String project;

    @Value("${GCP_REGION:us-east1}")
    private String region;

    @Value("${MCP_HOST:0.0.0.0}")
    private String host;

    @Value("${MCP_PORT:80}")
    private String port;

    @Value("${MCP_TRANSPORT:streamable-http}")
    private String transport;

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Map<String, Object>> handle(@RequestBody McpRequest request) {
        return switch (request.method()) {
            case "initialize" -> initialize(request.id());
            case "tools/list" -> toolsList(request.id());
            case "tools/call" -> toolsCall(request.id(), request.params());
            default -> jsonRpcError(request.id(), -32601, "Method not found");
        };
    }

    private ResponseEntity<Map<String, Object>> initialize(Object id) {
        return ResponseEntity.ok(Map.of(
                "jsonrpc", "2.0",
                "id", id,
                "result", Map.of(
                        "protocolVersion", "2025-03-26",
                        "serverInfo", Map.of("name", "sisacao-mcp-java", "version", "0.0.1"),
                        "capabilities", Map.of("tools", Map.of()),
                        "timestamp", Instant.now().toString())));
    }

    private ResponseEntity<Map<String, Object>> toolsList(Object id) {
        return ResponseEntity.ok(Map.of(
                "jsonrpc", "2.0",
                "id", id,
                "result", Map.of("tools", List.of(
                        tool("ping", "Ferramenta de diagnóstico para validar disponibilidade remota."),
                        tool("runtime_config", "Expõe configurações não sensíveis carregadas no runtime."),
                        tool("bigquery_access_check", "Valida autenticação e execução de query simples no BigQuery."),
                        tool("bigquery_query", "Executa query read-only no BigQuery (placeholder de migração Java)."),
                        tool("cloud_run_function_logs", "Retorna logs básicos (placeholder de migração Java).")))));
    }

    private ResponseEntity<Map<String, Object>> toolsCall(Object id, Map<String, Object> params) {
        String name = params == null ? null : String.valueOf(params.getOrDefault("name", ""));
        if (name == null || name.isBlank()) {
            return jsonRpcError(id, -32602, "Missing tool name");
        }

        Map<String, Object> arguments = Map.of();
        Object argsObj = params.get("arguments");
        if (argsObj instanceof Map<?, ?> castedArgs) {
            arguments = (Map<String, Object>) castedArgs;
        }

        return switch (name) {
            case "ping" -> toolResult(id, Map.of("status", "ok"));
            case "runtime_config" -> toolResult(id, Map.of(
                    "project", project,
                    "region", region,
                    "transport", transport,
                    "host", host,
                    "port", port));
            case "bigquery_access_check" -> toolResult(id, Map.of(
                    "status", "not_implemented",
                    "project", project,
                    "message", "Tool migrada para Java; integração BigQuery será conectada no próximo passo."));
            case "bigquery_query" -> toolResult(id, Map.of(
                    "status", "not_implemented",
                    "project", project,
                    "sql", String.valueOf(arguments.getOrDefault("sql", "")),
                    "message", "Tool criada com mesma assinatura lógica da versão Python."));
            case "cloud_run_function_logs" -> toolResult(id, Map.of(
                    "status", "not_implemented",
                    "project", project,
                    "region", region,
                    "service_name", String.valueOf(arguments.getOrDefault("service_name", "")),
                    "message", "Tool criada com mesma assinatura lógica da versão Python."));
            default -> jsonRpcError(id, -32601, "Tool not found: " + name);
        };
    }

    private ResponseEntity<Map<String, Object>> toolResult(Object id, Map<String, Object> content) {
        return ResponseEntity.ok(Map.of(
                "jsonrpc", "2.0",
                "id", id,
                "result", Map.of("content", List.of(Map.of("type", "json", "json", content)))));
    }

    private ResponseEntity<Map<String, Object>> jsonRpcError(Object id, int code, String message) {
        return ResponseEntity.ok(Map.of(
                "jsonrpc", "2.0",
                "id", id,
                "error", Map.of("code", code, "message", message)));
    }

    private Map<String, Object> tool(String name, String description) {
        Map<String, Object> tool = new LinkedHashMap<>();
        tool.put("name", name);
        tool.put("description", description);
        tool.put("inputSchema", Map.of("type", "object", "properties", Map.of()));
        return tool;
    }

    public record McpRequest(Object id, @NotBlank String method, Map<String, Object> params) {}
}
