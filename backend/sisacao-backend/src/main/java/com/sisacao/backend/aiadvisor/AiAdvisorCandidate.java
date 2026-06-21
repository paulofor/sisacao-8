package com.sisacao.backend.aiadvisor;

import java.util.Collections;
import java.util.Map;

public record AiAdvisorCandidate(
        String candidateId,
        Map<String, Object> architecture,
        Map<String, Object> hyperparameters,
        Map<String, Object> metadata) {

    public AiAdvisorCandidate {
        architecture = immutableMap(architecture);
        hyperparameters = immutableMap(hyperparameters);
        metadata = immutableMap(metadata);
    }

    private static Map<String, Object> immutableMap(Map<String, Object> value) {
        if (value == null || value.isEmpty()) {
            return Map.of();
        }
        return Collections.unmodifiableMap(value);
    }
}
