package com.sisacao.backend.aiadvisor;

import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public record AiAdvisorResponse(
        String advisorRunId,
        String provider,
        String model,
        String status,
        String rationale,
        List<AiAdvisorCandidate> candidates,
        List<String> rejectionReasons,
        Map<String, Object> rawResponse,
        Instant createdAt) {

    public AiAdvisorResponse {
        candidates = immutableList(candidates);
        rejectionReasons = immutableList(rejectionReasons);
        rawResponse = immutableMap(rawResponse);
        createdAt = createdAt == null ? Instant.now() : createdAt;
    }

    private static <T> List<T> immutableList(List<T> value) {
        if (value == null || value.isEmpty()) {
            return List.of();
        }
        return List.copyOf(value);
    }

    private static Map<String, Object> immutableMap(Map<String, Object> value) {
        if (value == null || value.isEmpty()) {
            return Map.of();
        }
        return Collections.unmodifiableMap(value);
    }
}
