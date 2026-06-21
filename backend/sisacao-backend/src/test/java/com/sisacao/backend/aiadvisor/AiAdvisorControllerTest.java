package com.sisacao.backend.aiadvisor;

import static org.hamcrest.Matchers.is;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(controllers = AiAdvisorController.class, properties = "sisacao.ai-advisor.enabled=true")
class AiAdvisorControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AiAdvisorService service;

    @Test
    void shouldReturnProviderAgnosticRecommendations() throws Exception {
        given(service.requestAdvice(any())).willReturn(new AiAdvisorResponse(
                "advisor-run-1",
                "test-provider",
                "test-model",
                "accepted",
                "generic provider response",
                List.of(new AiAdvisorCandidate(
                        "candidate-1",
                        Map.of("type", "mlp"),
                        Map.of("learning_rate", 0.001),
                        Map.of("risk", "low"))),
                List.of(),
                Map.of("provider", "test-provider"),
                Instant.parse("2026-06-21T00:00:00Z")));

        mockMvc.perform(post("/ai/advisor/recommendations")
                        .contentType("application/json")
                        .content("""
                                {
                                  "advisorRunId": "advisor-run-1",
                                  "task": "propose_candidates",
                                  "context": {"leaderboard": []},
                                  "constraints": {"maxTrials": 2},
                                  "expectedResponseSchema": {"type": "object"},
                                  "guardrails": ["return_json_only", "do_not_promote_models"]
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.provider", is("test-provider")))
                .andExpect(jsonPath("$.model", is("test-model")))
                .andExpect(jsonPath("$.candidates[0].candidateId", is("candidate-1")))
                .andExpect(jsonPath("$.candidates[0].hyperparameters.learning_rate", is(0.001)));
    }

    @Test
    void shouldMapValidationErrorsToBadRequest() throws Exception {
        given(service.requestAdvice(any())).willThrow(new AiAdvisorValidationException("task is required"));

        mockMvc.perform(post("/ai/advisor/recommendations")
                        .contentType("application/json")
                        .content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", is("task is required")));
    }
}
