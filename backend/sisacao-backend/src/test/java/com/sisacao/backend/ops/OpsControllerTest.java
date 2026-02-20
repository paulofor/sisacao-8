package com.sisacao.backend.ops;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(controllers = OpsController.class, properties = "sisacao.ops.bigquery.enabled=true")
@Import(OpsExceptionHandler.class)
class OpsControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private OpsService opsService;

    @Test
    void shouldReturnOverview() throws Exception {
        OpsOverview overview = new OpsOverview(
                OffsetDateTime.parse("2024-11-03T12:00:00Z"),
                java.time.LocalDate.parse("2024-11-01"),
                java.time.LocalDate.parse("2024-11-04"),
                "OK",
                "PASS",
                true,
                5L,
                OffsetDateTime.parse("2024-11-03T12:05:00Z"));
        given(opsService.getOverview()).willReturn(overview);

        mockMvc.perform(get("/ops/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pipelineHealth", is("OK")))
                .andExpect(jsonPath("$.signalsCount", is(5)))
                .andExpect(jsonPath("$.signalsReady", is(true)));
    }

    @Test
    void shouldReturnPipelineStatus() throws Exception {
        List<PipelineJobStatus> jobs = List.of(new PipelineJobStatus(
                "daily_ohlcv",
                OffsetDateTime.parse("2024-11-03T10:00:00Z"),
                "OK",
                25L,
                OffsetDateTime.parse("2024-11-03T22:00:00Z"),
                false,
                "run-123"));
        given(opsService.getPipelineStatus()).willReturn(jobs);

        mockMvc.perform(get("/ops/pipeline"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].jobName", is("daily_ohlcv")))
                .andExpect(jsonPath("$[0].isSilent", is(false)));
    }

    @Test
    void shouldReturnDqChecks() throws Exception {
        List<DqCheck> checks = List.of(new DqCheck(
                java.time.LocalDate.parse("2024-11-03"),
                "intraday_freshness",
                "PASS",
                "{\"coverage\":0.98}",
                OffsetDateTime.now(ZoneOffset.UTC)));
        given(opsService.getLatestDqChecks()).willReturn(checks);

        mockMvc.perform(get("/ops/dq/latest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].checkName", is("intraday_freshness")));
    }

    @Test
    void shouldReturnIncidents() throws Exception {
        List<OpsIncident> incidents = List.of(new OpsIncident(
                "inc-001",
                "intraday_uniqueness",
                java.time.LocalDate.parse("2024-11-03"),
                "HIGH",
                "DQ",
                "Duplicidade acima do limiar",
                "OPEN",
                "run-456",
                OffsetDateTime.now(ZoneOffset.UTC)));
        given(opsService.getOpenIncidents()).willReturn(incidents);

        mockMvc.perform(get("/ops/incidents/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].incidentId", is("inc-001")));
    }

    @Test
    void shouldReturnNextSignals() throws Exception {
        List<Signal> signals = List.of(new Signal(
                java.time.LocalDate.parse("2024-11-04"),
                "PETR4",
                "BUY",
                33.5,
                36.1,
                31.0,
                0.81,
                1,
                OffsetDateTime.now(ZoneOffset.UTC)));
        given(opsService.getNextSignals()).willReturn(signals);

        mockMvc.perform(get("/ops/signals/next"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].ticker", is("PETR4")));
    }

    @Test
    void shouldReturnSignalsHistory() throws Exception {
        List<SignalHistoryEntry> history = List.of(new SignalHistoryEntry(
                java.time.LocalDate.parse("2024-10-31"),
                java.time.LocalDate.parse("2024-11-01"),
                "VALE3",
                "SELL",
                70.0,
                66.0,
                72.0,
                -0.35,
                3,
                OffsetDateTime.now(ZoneOffset.UTC)));
        given(opsService.getSignalsHistory(java.time.LocalDate.parse("2024-11-01"), java.time.LocalDate.parse("2024-11-04"), null))
                .willReturn(history);

        mockMvc.perform(get("/ops/signals/history")
                        .param("from", "2024-11-01")
                        .param("to", "2024-11-04"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].ticker", is("VALE3")));
    }

    @Test
    void shouldRejectInvalidRange() throws Exception {
        given(opsService.getSignalsHistory(
                        java.time.LocalDate.parse("2024-11-10"),
                        java.time.LocalDate.parse("2024-11-01"),
                        null))
                .willThrow(new OpsValidationException("O parâmetro 'from' não pode ser posterior ao 'to'."));

        mockMvc.perform(get("/ops/signals/history")
                        .param("from", "2024-11-10")
                        .param("to", "2024-11-01"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", containsString("não pode ser posterior")));
    }

    @Test
    void shouldRejectInvalidDateFormat() throws Exception {
        mockMvc.perform(get("/ops/signals/history")
                        .param("from", "2024-13-01")
                        .param("to", "2024-11-01"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", containsString("formato YYYY-MM-DD")));
    }

    @Test
    void shouldMapDataAccessFailures() throws Exception {
        given(opsService.getOverview()).willThrow(new OpsDataAccessException("BigQuery indisponível"));

        mockMvc.perform(get("/ops/overview"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.message", containsString("BigQuery indisponível")));
    }
}
