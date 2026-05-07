package com.sisacao.mcpserver;

import jakarta.validation.constraints.NotBlank;
import jakarta.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/mcp")
@Validated
public class McpController {

    private static final String MCP_SESSION_ID_HEADER = "mcp-session-id";
    private static final Logger LOGGER = LoggerFactory.getLogger(McpController.class);

    private final Set<String> activeSessions = Collections.newSetFromMap(new ConcurrentHashMap<>());

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
    public ResponseEntity<Map<String, Object>> handle(
            @RequestBody McpRequest request,
            @RequestHeader(value = MCP_SESSION_ID_HEADER, required = false) String sessionId,
            HttpServletRequest httpRequest) {
        ResponseEntity<Map<String, Object>> response = switch (request.method()) {
            case "initialize" -> initialize(request.id());
            case "tools/list" -> withValidSession(request.id(), sessionId, () -> toolsList(request.id()));
            case "tools/call" -> withValidSession(request.id(), sessionId, () -> toolsCall(request.id(), request.params()));
            default -> jsonRpcError(request.id(), -32601, "Method not found");
        };

        LOGGER.info(
                "MCP request recebida | method={} | path={} | query={} | remoteAddr={} | mcpMethod={} | status={}",
                httpRequest.getMethod(),
                httpRequest.getRequestURI(),
                httpRequest.getQueryString(),
                httpRequest.getRemoteAddr(),
                request.method(),
                response.getStatusCode().value());
        return response;
    }

    private ResponseEntity<Map<String, Object>> initialize(Object id) {
        String sessionId = UUID.randomUUID().toString();
        activeSessions.add(sessionId);
        return ResponseEntity.ok()
                .header(MCP_SESSION_ID_HEADER, sessionId)
                .body(Map.of(
                "jsonrpc", "2.0",
                "id", id,
                "result", Map.of(
                        "protocolVersion", "2025-03-26",
                        "serverInfo", Map.of("name", "sisacao-mcp-java", "version", "0.0.1"),
                        "capabilities", Map.of("tools", Map.of()),
                        "timestamp", Instant.now().toString())));
    }

    private ResponseEntity<Map<String, Object>> withValidSession(
            Object id, String sessionId, SessionHandler handler) {
        if (sessionId == null || sessionId.isBlank()) {
            return jsonRpcError(id, -32001, "Missing mcp-session-id header");
        }
        if (!activeSessions.contains(sessionId)) {
            return jsonRpcError(id, -32002, "Invalid mcp-session-id header");
        }
        return handler.handle();
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
            case "cloud_run_function_logs" -> toolResult(id, cloudRunFunctionLogs(arguments));
            default -> jsonRpcError(id, -32601, "Tool not found: " + name);
        };
    }

    private Map<String, Object> cloudRunFunctionLogs(Map<String, Object> arguments) {
        String functionName = String.valueOf(arguments.getOrDefault("function_name", "")).trim();
        if (functionName.isBlank()) {
            return Map.of("status", "error", "message", "function_name vazio");
        }

        String severity = String.valueOf(arguments.getOrDefault("severity", "DEFAULT")).trim().toUpperCase();
        if (severity.isBlank()) {
            severity = "DEFAULT";
        }
        int limit = clampInt(arguments.get("limit"), 50, 1, 200);
        int hours = clampInt(arguments.get("hours"), 24, 1, 168);
        boolean includeAuditLogs = Boolean.parseBoolean(String.valueOf(arguments.getOrDefault("include_audit_logs", false)));

        String serviceName = functionName.replace("_", "-");
        List<String> command = new ArrayList<>(List.of(
                "gcloud", "run", "services", "logs", "read", serviceName,
                "--region", region,
                "--project", project,
                "--freshness", hours + "h",
                "--limit", String.valueOf(limit),
                "--format", "value(timestamp,textPayload)"));
        List<String> filters = new ArrayList<>();
        if (!"DEFAULT".equals(severity)) {
            filters.add("severity>=" + severity);
        }
        if (!includeAuditLogs) {
            filters.add("NOT logName:\"cloudaudit.googleapis.com\"");
        }
        if (!filters.isEmpty()) {
            command.add("--log-filter");
            command.add(String.join(" AND ", filters));
        }

        try {
            ProcessBuilder pb = new ProcessBuilder(command);
            Process process = pb.start();
            List<String> lines = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))
                    .lines()
                    .filter(line -> !line.isBlank())
                    .limit(limit)
                    .toList();
            String stderr = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))
                    .lines()
                    .reduce("", (a, b) -> a.isEmpty() ? b : a + "\n" + b);
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                return Map.of(
                        "status", "error",
                        "project", project,
                        "region", region,
                        "function_name", functionName,
                        "service_name", serviceName,
                        "command", String.join(" ", command),
                        "message", stderr.isBlank() ? "Falha ao executar gcloud." : stderr);
            }

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("status", "ok");
            response.put("project", project);
            response.put("region", region);
            response.put("function_name", functionName);
            response.put("service_name", serviceName);
            response.put("severity", severity);
            response.put("hours", hours);
            response.put("include_audit_logs", includeAuditLogs);
            response.put("row_count", lines.size());
            response.put("lines", lines);
            response.put("source", "gcloud_cli");
            response.put("command", String.join(" ", command));
            return response;
        } catch (Exception exc) {
            return Map.of(
                    "status", "error",
                    "project", project,
                    "region", region,
                    "function_name", functionName,
                    "service_name", serviceName,
                    "message", exc.getMessage());
        }
    }

    private int clampInt(Object rawValue, int defaultValue, int minValue, int maxValue) {
        try {
            int parsed = Integer.parseInt(String.valueOf(rawValue == null ? defaultValue : rawValue));
            return Math.max(minValue, Math.min(maxValue, parsed));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
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

    @FunctionalInterface
    private interface SessionHandler {
        ResponseEntity<Map<String, Object>> handle();
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
