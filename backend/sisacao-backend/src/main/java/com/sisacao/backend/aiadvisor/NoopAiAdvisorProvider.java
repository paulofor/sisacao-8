package com.sisacao.backend.aiadvisor;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(prefix = "sisacao.ai-advisor", name = "provider", havingValue = "noop", matchIfMissing = true)
public class NoopAiAdvisorProvider implements AiAdvisorProvider {

    static final String PROVIDER_ID = "noop";

    @Override
    public String providerId() {
        return PROVIDER_ID;
    }

    @Override
    public AiAdvisorResponse requestAdvice(AiAdvisorRequest request) {
        return new AiAdvisorResponse(
                request.advisorRunId(),
                PROVIDER_ID,
                "none",
                "skipped",
                "No AI provider configured; request accepted for contract validation only.",
                List.of(),
                List.of("provider_not_configured"),
                Map.of("task", request.task()),
                Instant.now());
    }
}
