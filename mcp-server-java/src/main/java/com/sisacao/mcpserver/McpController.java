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
    private static final String NEURAL_EVOLUTION_FUNCTION_URL =
            "https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator";
    private static final String SCHEDULER_INVOKER_SERVICE_ACCOUNT =
            "sa-scheduler-invoker@ingestaokraken.iam.gserviceaccount.com";
    private static final Pattern READ_ONLY_SQL_PATTERN = Pattern.compile("^\\s*(select|with)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern SCHEDULER_JOB_NAME_PATTERN =
            Pattern.compile("^[A-Za-z0-9][A-Za-z0-9_-]{0,499}$");

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
                        tool("cloud_scheduler_job", "Consulta um job do Cloud Scheduler via gcloud."),
                        tool("cloud_scheduler_job_write",
                                "Cria, atualiza, pausa, retoma, executa ou remove jobs do Cloud Scheduler via gcloud."),
                        tool("neural_evolution_daily_scheduler_apply",
                                "Cria/atualiza o Scheduler diário da evolução neural e pode pausar o semanal."),
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
            case "cloud_scheduler_job" -> toolResult(id, cloudSchedulerJob(arguments));
            case "cloud_scheduler_job_write" -> toolResult(id, cloudSchedulerJobWrite(arguments));
            case "neural_evolution_daily_scheduler_apply" -> toolResult(id, neuralEvolutionDailySchedulerApply(arguments));
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


    private Map<String, Object> cloudSchedulerJob(Map<String, Object> arguments) {
        String jobName = String.valueOf(arguments.getOrDefault("job_name", "")).trim();
        String jobNameError = validateSchedulerJobName(jobName);
        if (jobNameError != null) {
            return Map.of("status", "error", "message", jobNameError, "project", FIXED_PROJECT_ID);
        }

        String location = String.valueOf(arguments.getOrDefault("location", FIXED_REGION)).trim();
        if (location.isBlank()) {
            location = FIXED_REGION;
        }
        String format = String.valueOf(arguments.getOrDefault(
                "format",
                "yaml(name,state,schedule,timeZone,attemptDeadline,httpTarget.uri,httpTarget.httpMethod,httpTarget.body,nextRunTime,lastAttemptTime)"))
                .trim();
        if (format.isBlank()) {
            format = "json";
        }

        List<String> command = List.of(
                "gcloud", "scheduler", "jobs", "describe", jobName,
                "--project", FIXED_PROJECT_ID,
                "--location", location,
                "--format", format);
        return gcloudTextCommand(command, "cloud_scheduler_job", Map.of(
                "job_name", jobName,
                "location", location));
    }

    private Map<String, Object> cloudSchedulerJobWrite(Map<String, Object> arguments) {
        String action = String.valueOf(arguments.getOrDefault("action", "")).trim().toLowerCase();
        if (!List.of("create", "update", "pause", "resume", "run", "delete").contains(action)) {
            return Map.of(
                    "status", "error",
                    "project", FIXED_PROJECT_ID,
                    "message", "action deve ser create, update, pause, resume, run ou delete");
        }

        String jobName = String.valueOf(arguments.getOrDefault("job_name", "")).trim();
        String jobNameError = validateSchedulerJobName(jobName);
        if (jobNameError != null) {
            return Map.of("status", "error", "message", jobNameError, "project", FIXED_PROJECT_ID);
        }

        String location = String.valueOf(arguments.getOrDefault("location", FIXED_REGION)).trim();
        if (location.isBlank()) {
            location = FIXED_REGION;
        }

        List<String> command = new ArrayList<>(List.of("gcloud", "scheduler", "jobs", action));
        if (List.of("create", "update").contains(action)) {
            String uri = String.valueOf(arguments.getOrDefault("uri", arguments.getOrDefault("target_uri", ""))).trim();
            String uriError = validateSchedulerTargetUri(uri);
            if (uriError != null) {
                return Map.of("status", "error", "message", uriError, "project", FIXED_PROJECT_ID);
            }

            String schedule = String.valueOf(arguments.getOrDefault("schedule", "0 6 * * *")).trim();
            if (schedule.isBlank()) {
                schedule = "0 6 * * *";
            }
            String timeZone = String.valueOf(arguments.getOrDefault("time_zone", "America/Sao_Paulo")).trim();
            if (timeZone.isBlank()) {
                timeZone = "America/Sao_Paulo";
            }
            String httpMethod = String.valueOf(arguments.getOrDefault("http_method", "POST")).trim().toUpperCase();
            if (!List.of("GET", "POST", "PUT", "PATCH", "DELETE").contains(httpMethod)) {
                return Map.of("status", "error", "message", "http_method inválido", "project", FIXED_PROJECT_ID);
            }
            String attemptDeadline = String.valueOf(arguments.getOrDefault("attempt_deadline", "1800s")).trim();
            if (attemptDeadline.isBlank()) {
                attemptDeadline = "1800s";
            }
            String headers = String.valueOf(arguments.getOrDefault("headers", "Content-Type=application/json")).trim();
            if (headers.isBlank()) {
                headers = "Content-Type=application/json";
            }
            String messageBody = String.valueOf(arguments.getOrDefault("message_body", "")).trim();

            command.add("http");
            command.add(jobName);
            command.add("--project");
            command.add(FIXED_PROJECT_ID);
            command.add("--location");
            command.add(location);
            command.add("--schedule");
            command.add(schedule);
            command.add("--time-zone");
            command.add(timeZone);
            command.add("--uri");
            command.add(uri);
            command.add("--http-method");
            command.add(httpMethod);
            command.add("--attempt-deadline");
            command.add(attemptDeadline);
            command.add("--headers");
            command.add(headers);
            if (!messageBody.isBlank()) {
                command.add("--message-body");
                command.add(messageBody);
            }

            boolean useOidc = Boolean.parseBoolean(String.valueOf(arguments.getOrDefault("oidc", false)));
            if (useOidc) {
                String serviceAccount = String.valueOf(arguments.getOrDefault(
                        "oidc_service_account_email",
                        SCHEDULER_INVOKER_SERVICE_ACCOUNT)).trim();
                if (!serviceAccount.endsWith("@ingestaokraken.iam.gserviceaccount.com")) {
                    return Map.of(
                            "status", "error",
                            "message", "oidc_service_account_email deve pertencer ao projeto ingestaokraken",
                            "project", FIXED_PROJECT_ID);
                }
                String audience = String.valueOf(arguments.getOrDefault("oidc_token_audience", uri)).trim();
                command.add("--oidc-service-account-email");
                command.add(serviceAccount);
                command.add("--oidc-token-audience");
                command.add(audience);
            }
        } else {
            command.add(jobName);
            command.add("--project");
            command.add(FIXED_PROJECT_ID);
            command.add("--location");
            command.add(location);
            if ("delete".equals(action)) {
                command.add("--quiet");
            }
        }

        return gcloudTextCommand(command, "cloud_scheduler_job_write", Map.of(
                "job_name", jobName,
                "operation", action,
                "location", location));
    }

    private Map<String, Object> neuralEvolutionDailySchedulerApply(Map<String, Object> arguments) {
        String location = String.valueOf(arguments.getOrDefault("location", FIXED_REGION)).trim();
        if (location.isBlank()) {
            location = FIXED_REGION;
        }
        String schedule = String.valueOf(arguments.getOrDefault("schedule", "0 6 * * *")).trim();
        if (schedule.isBlank()) {
            schedule = "0 6 * * *";
        }
        String timeZone = String.valueOf(arguments.getOrDefault("time_zone", "America/Sao_Paulo")).trim();
        if (timeZone.isBlank()) {
            timeZone = "America/Sao_Paulo";
        }
        int maxTrials = clampInt(arguments.get("max_trials"), 3, 1, 5);
        int maxRuntimeMinutes = clampInt(arguments.get("max_runtime_minutes"), 120, 30, 240);
        boolean pauseWeekly = Boolean.parseBoolean(String.valueOf(arguments.getOrDefault("pause_weekly", true)));
        boolean useOidc = Boolean.parseBoolean(String.valueOf(arguments.getOrDefault("oidc", false)));

        String messageBody = String.format(
                "{\"strategy\":\"deterministic_phase1\",\"budget\":{\"max_trials\":%d,"
                        + "\"max_runtime_minutes\":%d,\"max_parameter_count\":150000,"
                        + "\"max_layers\":4,\"random_seed\":20260621}}",
                maxTrials,
                maxRuntimeMinutes);

        List<String> baseCommand = new ArrayList<>(List.of(
                "gcloud", "scheduler", "jobs", "update", "http", "neural-evolution-daily",
                "--project", FIXED_PROJECT_ID,
                "--location", location,
                "--schedule", schedule,
                "--time-zone", timeZone,
                "--uri", NEURAL_EVOLUTION_FUNCTION_URL,
                "--http-method", "POST",
                "--attempt-deadline", "1800s",
                "--headers", "Content-Type=application/json",
                "--message-body", messageBody));
        if (useOidc) {
            baseCommand.add("--oidc-service-account-email");
            baseCommand.add(SCHEDULER_INVOKER_SERVICE_ACCOUNT);
            baseCommand.add("--oidc-token-audience");
            baseCommand.add(NEURAL_EVOLUTION_FUNCTION_URL);
        }

        Map<String, Object> updateResult = gcloudTextCommand(
                baseCommand,
                "neural_evolution_daily_scheduler_apply",
                Map.of("job_name", "neural-evolution-daily", "operation", "update", "location", location));

        List<Map<String, Object>> operations = new ArrayList<>();
        operations.add(updateResult);
        Map<String, Object> applyResult = updateResult;
        if (!"ok".equals(updateResult.get("status"))) {
            List<String> createCommand = new ArrayList<>(baseCommand);
            createCommand.set(3, "create");
            applyResult = gcloudTextCommand(
                    createCommand,
                    "neural_evolution_daily_scheduler_apply",
                    Map.of("job_name", "neural-evolution-daily", "operation", "create", "location", location));
            operations.add(applyResult);
        }

        if (pauseWeekly) {
            Map<String, Object> pauseResult = gcloudTextCommand(
                    List.of(
                            "gcloud", "scheduler", "jobs", "pause", "neural-evolution-weekly",
                            "--project", FIXED_PROJECT_ID,
                            "--location", location),
                    "neural_evolution_daily_scheduler_apply",
                    Map.of("job_name", "neural-evolution-weekly", "operation", "pause", "location", location));
            operations.add(pauseResult);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "ok".equals(applyResult.get("status")) ? "ok" : "error");
        response.put("project", FIXED_PROJECT_ID);
        response.put("region", FIXED_REGION);
        response.put("tool", "neural_evolution_daily_scheduler_apply");
        response.put("job_name", "neural-evolution-daily");
        response.put("schedule", schedule);
        response.put("time_zone", timeZone);
        response.put("max_trials", maxTrials);
        response.put("max_runtime_minutes", maxRuntimeMinutes);
        response.put("pause_weekly", pauseWeekly);
        response.put("operations", operations);
        return response;
    }

    private String validateSchedulerJobName(String jobName) {
        if (jobName == null || jobName.isBlank()) {
            return "job_name vazio";
        }
        if (!SCHEDULER_JOB_NAME_PATTERN.matcher(jobName).matches()) {
            return "job_name inválido";
        }
        return null;
    }

    private String validateSchedulerTargetUri(String uri) {
        if (uri == null || uri.isBlank()) {
            return "uri vazio";
        }
        if (!uri.startsWith("https://us-east1-ingestaokraken.cloudfunctions.net/")
                && !uri.startsWith("https://")
                && !uri.startsWith("http://34.194.252.70/")) {
            return "uri fora dos alvos HTTP permitidos";
        }
        return null;
    }

    private Map<String, Object> gcloudTextCommand(
            List<String> command,
            String toolName,
            Map<String, Object> metadata) {
        String joinedCommand = String.join(" ", command);
        LOGGER.info("Executando comando gcloud para {} | command={}", toolName, joinedCommand);

        try {
            Process process = new ProcessBuilder(command).start();
            String stdout = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))
                    .lines()
                    .reduce("", (a, b) -> a.isEmpty() ? b : a + "\n" + b);
            String stderr = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))
                    .lines()
                    .reduce("", (a, b) -> a.isEmpty() ? b : a + "\n" + b);
            int exitCode = process.waitFor();

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("status", exitCode == 0 ? "ok" : "error");
            response.put("project", FIXED_PROJECT_ID);
            response.put("region", FIXED_REGION);
            response.put("tool", toolName);
            response.put("command", joinedCommand);
            response.put("source", "gcloud_cli");
            response.putAll(metadata);
            if (exitCode == 0) {
                response.put("output", stdout);
            } else {
                response.put("message", stderr.isBlank() ? "Falha ao executar gcloud." : stderr);
            }
            return response;
        } catch (Exception exc) {
            Map<String, Object> errorResponse = new LinkedHashMap<>();
            errorResponse.put("status", "error");
            errorResponse.put("project", FIXED_PROJECT_ID);
            errorResponse.put("region", FIXED_REGION);
            errorResponse.put("tool", toolName);
            errorResponse.put("command", joinedCommand);
            errorResponse.put("source", "gcloud_cli");
            errorResponse.putAll(metadata);
            errorResponse.put("message", exc.getMessage());
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
