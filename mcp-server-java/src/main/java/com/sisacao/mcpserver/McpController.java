package com.sisacao.mcpserver;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;
import java.util.Map;
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

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Map<String, Object>> handle(@RequestBody McpRequest request) {
        return switch (request.method()) {
            case "initialize" -> ResponseEntity.ok(Map.of(
                    "jsonrpc", "2.0",
                    "id", request.id(),
                    "result", Map.of(
                            "protocolVersion", "2025-03-26",
                            "serverInfo", Map.of("name", "sisacao-mcp-java", "version", "0.0.1"),
                            "capabilities", Map.of("tools", Map.of()),
                            "timestamp", Instant.now().toString())));
            case "tools/list" -> ResponseEntity.ok(Map.of(
                    "jsonrpc", "2.0",
                    "id", request.id(),
                    "result", Map.of("tools", List.of())));
            default -> ResponseEntity.ok(Map.of(
                    "jsonrpc", "2.0",
                    "id", request.id(),
                    "error", Map.of("code", -32601, "message", "Method not found")));
        };
    }

    public record McpRequest(Object id, @NotBlank String method, Map<String, Object> params) {}
}
