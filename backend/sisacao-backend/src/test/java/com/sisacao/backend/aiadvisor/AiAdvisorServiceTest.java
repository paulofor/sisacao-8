package com.sisacao.backend.aiadvisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AiAdvisorServiceTest {

    @Test
    void shouldDelegateToConfiguredProvider() {
        AiAdvisorProperties properties = new AiAdvisorProperties();
        properties.setProvider("test-provider");
        AiAdvisorService service = new AiAdvisorService(properties, List.of(new TestProvider()));

        AiAdvisorResponse response = service.requestAdvice(validRequest());

        assertThat(response.provider()).isEqualTo("test-provider");
        assertThat(response.status()).isEqualTo("accepted");
        assertThat(response.candidates()).hasSize(1);
        assertThat(response.candidates().getFirst().hyperparameters()).containsEntry("learning_rate", 0.001);
    }

    @Test
    void shouldRejectRequestsWithoutMandatoryGuardrail() {
        AiAdvisorProperties properties = new AiAdvisorProperties();
        AiAdvisorService service = new AiAdvisorService(properties, List.of(new NoopAiAdvisorProvider()));
        AiAdvisorRequest request = new AiAdvisorRequest(
                "advisor-run-1",
                "propose_candidates",
                Map.of("leaderboard", List.of()),
                Map.of("maxTrials", 2),
                Map.of("type", "object"),
                List.of("return_json_only"));

        assertThatThrownBy(() -> service.requestAdvice(request))
                .isInstanceOf(AiAdvisorValidationException.class)
                .hasMessageContaining("do_not_promote_models");
    }

    @Test
    void shouldRejectProviderResponsesAboveMaxCandidates() {
        AiAdvisorProperties properties = new AiAdvisorProperties();
        properties.setProvider("test-provider");
        properties.setMaxCandidates(0);
        AiAdvisorService service = new AiAdvisorService(properties, List.of(new TestProvider()));

        assertThatThrownBy(() -> service.requestAdvice(validRequest()))
                .isInstanceOf(AiAdvisorValidationException.class)
                .hasMessageContaining("maxCandidates");
    }

    private static AiAdvisorRequest validRequest() {
        return new AiAdvisorRequest(
                "advisor-run-1",
                "propose_candidates",
                Map.of("leaderboard", List.of()),
                Map.of("maxTrials", 2),
                Map.of("type", "object"),
                List.of("return_json_only", "do_not_promote_models", "respect_budget_and_search_space"));
    }

    private static class TestProvider implements AiAdvisorProvider {

        @Override
        public String providerId() {
            return "test-provider";
        }

        @Override
        public AiAdvisorResponse requestAdvice(AiAdvisorRequest request) {
            return new AiAdvisorResponse(
                    request.advisorRunId(),
                    providerId(),
                    "provider-model",
                    "accepted",
                    "validated by test provider",
                    List.of(new AiAdvisorCandidate(
                            "candidate-1",
                            Map.of("type", "mlp"),
                            Map.of("learning_rate", 0.001),
                            Map.of("source", "unit-test"))),
                    List.of(),
                    Map.of("provider", providerId()),
                    Instant.parse("2026-06-21T00:00:00Z"));
        }
    }
}
