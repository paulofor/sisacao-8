package com.sisacao.backend.aiadvisor;

import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
@ConditionalOnProperty(prefix = "sisacao.ai-advisor", name = "enabled", havingValue = "true")
public class AiAdvisorService {

    private final AiAdvisorProperties properties;
    private final List<AiAdvisorProvider> providers;

    public AiAdvisorService(AiAdvisorProperties properties, List<AiAdvisorProvider> providers) {
        this.properties = properties;
        this.providers = List.copyOf(providers);
    }

    public AiAdvisorResponse requestAdvice(AiAdvisorRequest request) {
        validateRequest(request);
        AiAdvisorProvider provider = providers.stream()
                .filter(candidate -> candidate.providerId().equalsIgnoreCase(properties.getProvider()))
                .findFirst()
                .orElseThrow(() -> new AiAdvisorValidationException(
                        "AI advisor provider not configured: " + properties.getProvider()));
        AiAdvisorResponse response = provider.requestAdvice(request);
        if (response.candidates().size() > properties.getMaxCandidates()) {
            throw new AiAdvisorValidationException("AI advisor response exceeded maxCandidates");
        }
        return response;
    }

    private void validateRequest(AiAdvisorRequest request) {
        if (request == null) {
            throw new AiAdvisorValidationException("request is required");
        }
        if (!StringUtils.hasText(request.advisorRunId())) {
            throw new AiAdvisorValidationException("advisorRunId is required");
        }
        if (!StringUtils.hasText(request.task())) {
            throw new AiAdvisorValidationException("task is required");
        }
        if (request.expectedResponseSchema().isEmpty()) {
            throw new AiAdvisorValidationException("expectedResponseSchema is required");
        }
        if (request.guardrails().stream().noneMatch("do_not_promote_models"::equals)) {
            throw new AiAdvisorValidationException("guardrail do_not_promote_models is required");
        }
    }
}
