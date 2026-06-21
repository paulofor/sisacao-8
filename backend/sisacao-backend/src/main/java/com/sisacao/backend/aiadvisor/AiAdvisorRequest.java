package com.sisacao.backend.aiadvisor;

import java.util.Collections;
import java.util.List;
import java.util.Map;

public record AiAdvisorRequest(
        String advisorRunId,
        String task,
        Map<String, Object> context,
        Map<String, Object> constraints,
        Map<String, Object> expectedResponseSchema,
        List<String> guardrails) {

    public AiAdvisorRequest {
        context = immutableMap(context);
        constraints = immutableMap(constraints);
        expectedResponseSchema = immutableMap(expectedResponseSchema);
        guardrails = immutableList(guardrails);
    }

    private static Map<String, Object> immutableMap(Map<String, Object> value) {
        if (value == null || value.isEmpty()) {
            return Map.of();
        }
        return Collections.unmodifiableMap(value);
    }

    private static List<String> immutableList(List<String> value) {
        if (value == null || value.isEmpty()) {
            return List.of();
        }
        return List.copyOf(value);
    }
}
