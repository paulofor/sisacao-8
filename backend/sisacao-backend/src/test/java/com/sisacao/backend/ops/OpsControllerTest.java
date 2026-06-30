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
    void shouldReturnNeuralTrainingDataAllocationWithTargetAndStopCounts() throws Exception {
        List<NeuralTrainingDataAllocation> allocation = List.of(new NeuralTrainingDataAllocation(
                "feature_eod_tabular_v1",
                "label_eod_barrier_v1",
                "train",
                100L,
                12L,
                java.time.LocalDate.parse("2026-03-30"),
                java.time.LocalDate.parse("2026-06-17"),
                30L,
                25L,
                45L,
                0.30,
                0.25,
                0.45,
                0L,
                1L,
                2L,
                18L,
                7L));
        given(opsService.getNeuralTrainingDataAllocation()).willReturn(allocation);

        mockMvc.perform(get("/ops/neural/training-data/allocation"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].datasetSplit", is("train")))
                .andExpect(jsonPath("$[0].targetHitCount", is(18)))
                .andExpect(jsonPath("$[0].stopHitCount", is(7)));
    }


    @Test
    void shouldReturnNeuralTrainingRuns() throws Exception {
        List<NeuralTrainingRun> runs = List.of(new NeuralTrainingRun(
                "neural_eod_mlp",
                "neural_eod_mlp_v1_20260618",
                "candidate",
                "feature_eod_tabular_v1",
                "label_eod_barrier_v1",
                "snapshot-123",
                "gs://models/neural_eod_mlp_v1_20260618/model.keras",
                19L,
                3L,
                0.61,
                0.42,
                0.58,
                0.55,
                "{\"test\":{\"accuracy\":0.55,\"rows_count\":120}}",
                "[[10,1,2],[1,8,1],[2,1,11]]",
                OffsetDateTime.parse("2026-06-18T20:30:00Z"),
                OffsetDateTime.parse("2026-06-18T20:35:00Z"),
                "Baseline inicial",
                138L,
                122L,
                3L,
                11L,
                2L,
                37L,
                99L));
        given(opsService.getNeuralTrainingRuns()).willReturn(runs);

        mockMvc.perform(get("/ops/neural/training-runs"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].modelId", is("neural_eod_mlp")))
                .andExpect(jsonPath("$[0].status", is("candidate")))
                .andExpect(jsonPath("$[0].testAccuracy", is(0.55)))
                .andExpect(jsonPath("$[0].metricsJson", is("{\"test\":{\"accuracy\":0.55,\"rows_count\":120}}")))
                .andExpect(jsonPath("$[0].totalRuns", is(138)))
                .andExpect(jsonPath("$[0].candidateRuns", is(122)))
                .andExpect(jsonPath("$[0].approvedRuns", is(3)))
                .andExpect(jsonPath("$[0].rejectedRuns", is(11)))
                .andExpect(jsonPath("$[0].activeTrainingRuns", is(2)))
                .andExpect(jsonPath("$[0].phase3Runs", is(37)))
                .andExpect(jsonPath("$[0].pendingGateCandidateRuns", is(99)));
    }

    @Test
    void shouldReturnNeuralGateDecisions() throws Exception {
        List<NeuralGateDecisionAttempt> attempts = List.of(new NeuralGateDecisionAttempt(
                "gate_abc",
                "neural_eod_protocol_v1",
                "snapshot-v2",
                "family-hash",
                "research_gate",
                "rejected",
                false,
                "drawdown_excessivo, seeds_instaveis",
                "{\"passed\":false}",
                "muen_research_gate_v1",
                OffsetDateTime.parse("2026-06-28T03:17:00Z"),
                4L,
                1L,
                1L,
                0.25,
                -0.01,
                0.02,
                -0.08,
                120L,
                false,
                78L,
                76L,
                2L));
        given(opsService.getNeuralGateDecisions()).willReturn(attempts);

        mockMvc.perform(get("/ops/neural/gate-decisions"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].decisionId", is("gate_abc")))
                .andExpect(jsonPath("$[0].decisionStatus", is("rejected")))
                .andExpect(jsonPath("$[0].failedCriteria", containsString("drawdown_excessivo")))
                .andExpect(jsonPath("$[0].folds", is(4)))
                .andExpect(jsonPath("$[0].stableAcrossSeeds", is(false)))
                .andExpect(jsonPath("$[0].totalDecisions", is(78)))
                .andExpect(jsonPath("$[0].rejectedDecisions", is(76)))
                .andExpect(jsonPath("$[0].passedDecisions", is(2)));
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
    void shouldReturnSignalsByDateWithNextTradingDayRange() throws Exception {
        List<SignalByDateEntry> signals = List.of(new SignalByDateEntry(
                java.time.LocalDate.parse("2024-10-31"),
                java.time.LocalDate.parse("2024-11-01"),
                "VALE3",
                "BUY",
                70.0,
                74.0,
                68.0,
                0.82,
                1,
                OffsetDateTime.now(ZoneOffset.UTC),
                java.time.LocalDate.parse("2024-11-01"),
                75.5,
                69.8));
        given(opsService.getSignalsByDate(java.time.LocalDate.parse("2024-10-31"))).willReturn(signals);

        mockMvc.perform(get("/ops/signals/by-date").param("date", "2024-10-31"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].ticker", is("VALE3")))
                .andExpect(jsonPath("$[0].nextTradingDay", is("2024-11-01")))
                .andExpect(jsonPath("$[0].nextDayHigh", is(75.5)))
                .andExpect(jsonPath("$[0].nextDayLow", is(69.8)));
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
