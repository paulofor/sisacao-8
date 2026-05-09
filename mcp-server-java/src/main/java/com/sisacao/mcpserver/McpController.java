package com.sisacao.mcpserver;

import jakarta.validation.constraints.NotBlank;
import jakarta.servlet.http.HttpServletRequest;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import java.util.regex.Pattern;
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
    private static final String FIXED_PROJECT_ID = "ingestaokraken";
    private static final String FIXED_REGION = "us-east1";
    private static final String BACKEND_ACTUATOR_LOG_URL = "http://34.194.252.70/api/actuator/logs/backend";
    private static final Pattern READ_ONLY_SQL_PATTERN = Pattern.compile("^\\s*(select|with)\\b", Pattern.CASE_INSENSITIVE);

    private final Set<String> activeSessions = Collections.newSetFromMap(new ConcurrentHashMap<>());
    private final ObjectMapper objectMapper;

    public McpController(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Value("${MCP_HOST:0.0.0.0}")
    private String host;

    @Value("${MCP_PORT:80}")
    private String port;

    @Value("${MCP_TRANSPORT:streamable-http}")
    private String transport;

    @Value("${K_SERVICE:sisacao-mcp-java}")
    private String cloudRunServiceName;

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
                        tool("bigquery_query", "Executa query read-only no BigQuery com limite de linhas."),
                        tool("mcp_server_logs", "Retorna logs do próprio MCP Server Java no Cloud Run."),
                        tool("cloud_run_function_logs", "Retorna logs básicos (placeholder de migração Java)."),
                        tool("backend_actuator_logs_url", "Retorna a URL pública de logs do backend para consumo via RPC-JSON.")))));
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
                    "project", FIXED_PROJECT_ID,
                    "region", FIXED_REGION,
                    "transport", transport,
                    "host", host,
                    "port", port));
            case "bigquery_access_check" -> toolResult(id, Map.of(
                    "status", "not_implemented",
                    "project", FIXED_PROJECT_ID,
                    "message", "Tool migrada para Java; integração BigQuery será conectada no próximo passo."));
            case "bigquery_query" -> toolResult(id, bigqueryQuery(arguments));
            case "mcp_server_logs" -> toolResult(id, mcpServerLogs(arguments));
            case "cloud_run_function_logs" -> toolResult(id, cloudRunFunctionLogs(arguments));
            case "backend_actuator_logs_url" -> toolResult(id, Map.of(
                    "status", "ok",
                    "url", BACKEND_ACTUATOR_LOG_URL,
                    "method", "GET"));
            default -> jsonRpcError(id, -32601, "Tool not found: " + name);
        };
    }

    private Map<String, Object> mcpServerLogs(Map<String, Object> arguments) {
        String serviceName = String.valueOf(arguments.getOrDefault("service_name", cloudRunServiceName)).trim();
        if (serviceName.isBlank()) {
            serviceName = cloudRunServiceName;
        }
        String severity = String.valueOf(arguments.getOrDefault("severity", "DEFAULT")).trim().toUpperCase();
        if (severity.isBlank()) {
            severity = "DEFAULT";
        }
        int limit = clampInt(arguments.get("limit"), 50, 1, 200);
        int hours = clampInt(arguments.get("hours"), 24, 1, 168);
        boolean includeAuditLogs = Boolean.parseBoolean(String.valueOf(arguments.getOrDefault("include_audit_logs", false)));
        return cloudRunLogsRead(serviceName, severity, limit, hours, includeAuditLogs, "mcp_server_logs");
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
        return cloudRunLogsRead(serviceName, severity, limit, hours, includeAuditLogs, "cloud_run_function_logs", functionName);
    }

    private Map<String, Object> cloudRunLogsRead(
            String serviceName,
            String severity,
            int limit,
            int hours,
            boolean includeAuditLogs,
            String toolName,
            String... functionNameOpt) {
        List<String> command = new ArrayList<>(List.of(
                "gcloud", "run", "services", "logs", "read", serviceName,
                "--region", FIXED_REGION,
                "--project", FIXED_PROJECT_ID,
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

        String joinedCommand = String.join(" ", command);
        LOGGER.info(
                "Executando comando gcloud para {} | function_name={} | service_name={} | command={}",
                toolName,
                functionNameOpt.length > 0 ? functionNameOpt[0] : "<none>",
                serviceName,
                joinedCommand);

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
            LOGGER.info(
                    "Resposta do comando gcloud | tool={} | function_name={} | service_name={} | exit_code={} | stdout_lines={} | stderr={}",
                    toolName,
                    functionNameOpt.length > 0 ? functionNameOpt[0] : "<none>",
                    serviceName,
                    exitCode,
                    lines.size(),
                    stderr.isBlank() ? "<empty>" : stderr);
            if (exitCode != 0) {
                LOGGER.error(
                        "Falha no comando gcloud | tool={} | function_name={} | service_name={} | command={} | exit_code={} | stderr={}",
                        toolName,
                        functionNameOpt.length > 0 ? functionNameOpt[0] : "<none>",
                        serviceName,
                        joinedCommand,
                        exitCode,
                        stderr.isBlank() ? "<empty>" : stderr);
                Map<String, Object> errorResponse = new LinkedHashMap<>();
                errorResponse.put("status", "error");
                errorResponse.put("project", FIXED_PROJECT_ID);
                errorResponse.put("region", FIXED_REGION);
                errorResponse.put("service_name", serviceName);
                errorResponse.put("tool", toolName);
                errorResponse.put("command", joinedCommand);
                errorResponse.put("message", stderr.isBlank() ? "Falha ao executar gcloud." : stderr);
                if (functionNameOpt.length > 0) {
                    errorResponse.put("function_name", functionNameOpt[0]);
                }
                return errorResponse;
            }

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("status", "ok");
            response.put("project", FIXED_PROJECT_ID);
            response.put("region", FIXED_REGION);
            if (functionNameOpt.length > 0) {
                response.put("function_name", functionNameOpt[0]);
            }
            response.put("service_name", serviceName);
            response.put("severity", severity);
            response.put("hours", hours);
            response.put("include_audit_logs", includeAuditLogs);
            response.put("row_count", lines.size());
            response.put("lines", lines);
            response.put("source", "gcloud_cli");
            response.put("tool", toolName);
            response.put("command", joinedCommand);
            return response;
        } catch (Exception exc) {
            LOGGER.error(
                    "Exceção ao executar comando gcloud | tool={} | function_name={} | service_name={} | command={} | message={}",
                    toolName,
                    functionNameOpt.length > 0 ? functionNameOpt[0] : "<none>",
                    serviceName,
                    joinedCommand,
                    exc.getMessage(),
                    exc);
            Map<String, Object> errorResponse = new LinkedHashMap<>();
            errorResponse.put("status", "error");
            errorResponse.put("project", FIXED_PROJECT_ID);
            errorResponse.put("region", FIXED_REGION);
            errorResponse.put("service_name", serviceName);
            errorResponse.put("tool", toolName);
            errorResponse.put("message", exc.getMessage());
            if (functionNameOpt.length > 0) {
                errorResponse.put("function_name", functionNameOpt[0]);
            }
            return errorResponse;
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

    private Map<String, Object> bigqueryQuery(Map<String, Object> arguments) {
        String sql = String.valueOf(arguments.getOrDefault("sql", arguments.getOrDefault("query", ""))).trim();
        if (sql.isBlank()) {
            return Map.of("status", "error", "message", "sql vazio", "project", FIXED_PROJECT_ID);
        }
        String normalizedNoTrailingSemicolon = sql.replaceAll(";+\\s*$", "");
        if (normalizedNoTrailingSemicolon.contains(";")) {
            return Map.of("status", "error", "message", "múltiplas instruções SQL não são permitidas", "project", FIXED_PROJECT_ID);
        }
        if (!READ_ONLY_SQL_PATTERN.matcher(sql).find()) {
            return Map.of("status", "error", "message", "apenas queries read-only iniciadas com SELECT ou WITH", "project", FIXED_PROJECT_ID);
        }

        int maxRows = clampInt(arguments.get("max_rows"), 200, 1, 2000);
        List<String> command = List.of(
                "bq", "query", "--project_id=" + FIXED_PROJECT_ID,
                "--use_legacy_sql=false", "--format=json", "--max_rows=" + maxRows, sql);
        try {
            Process process = new ProcessBuilder(command).start();
            String stdout = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))
                    .lines().reduce("", (a, b) -> a.isEmpty() ? b : a + "\n" + b);
            String stderr = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))
                    .lines().reduce("", (a, b) -> a.isEmpty() ? b : a + "\n" + b);
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                return Map.of(
                        "status", "error",
                        "project", FIXED_PROJECT_ID,
                        "message", stderr.isBlank() ? "Falha ao executar bq query." : stderr,
                        "sql", sql);
            }
            List<Map<String, Object>> rows = stdout.isBlank()
                    ? List.of()
                    : objectMapper.readValue(stdout, new TypeReference<List<Map<String, Object>>>() {});
            return Map.of(
                    "status", "ok",
                    "project", FIXED_PROJECT_ID,
                    "row_count", rows.size(),
                    "max_rows", maxRows,
                    "rows", rows,
                    "sql", sql,
                    "source", "bq_cli");
        } catch (Exception exc) {
            return Map.of(
                    "status", "error",
                    "project", FIXED_PROJECT_ID,
                    "message", exc.getMessage(),
                    "sql", sql);
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
