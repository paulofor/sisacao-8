package com.sisacao.backend.datacollection;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class DataCollectionMessageControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private PythonDataCollectionClient pythonClient;

    @MockBean
    private BigQueryIntradayMetricsClient intradayMetricsClient;

    @BeforeEach
    void setUpMocks() {
        given(pythonClient.fetchMessages()).willAnswer(invocation -> sampleMessages());
        given(intradayMetricsClient.fetchDailyCounts()).willReturn(sampleIntradayCounts());
    }

    @Test
    void shouldReturnAllMessages() throws Exception {
        mockMvc.perform(get("/data-collections/messages"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(5)))
                .andExpect(jsonPath("$[0].id", is("evt-001")))
                .andExpect(jsonPath("$[0].severity", is("SUCCESS")));
    }

    @Test
    void shouldFilterMessagesBySeverityAndCollector() throws Exception {
        mockMvc.perform(get("/data-collections/messages")
                        .param("severity", "warning")
                        .param("collector", "ingestao-crypto"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is("evt-002")))
                .andExpect(jsonPath("$[0].severity", is("WARNING")))
                .andExpect(jsonPath("$[0].collector", is("ingestao-crypto")));
    }

    @Test
    void shouldRespectLimitParameter() throws Exception {
        mockMvc.perform(get("/data-collections/messages").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].id", is("evt-001")))
                .andExpect(jsonPath("$[1].id", is("evt-002")));
    }

    @Test
    void shouldReturnIntradaySummary() throws Exception {
        mockMvc.perform(get("/data-collections/intraday-summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalTickers", is(3)))
                .andExpect(jsonPath("$.successfulTickers", is(2)))
                .andExpect(jsonPath("$.failedTickers", is(1)))
                .andExpect(jsonPath("$.tickers", hasSize(3)))
                .andExpect(jsonPath("$.tickers[0].ticker", is("PETR4")))
                .andExpect(jsonPath("$.tickers[0].price", is(32.1)))
                .andExpect(jsonPath("$.tickers[0].success", is(true)))
                .andExpect(jsonPath("$.tickers[2].ticker", is("BBAS3")))
                .andExpect(jsonPath("$.tickers[2].success", is(false)))
                .andExpect(jsonPath("$.tickers[2].error", containsString("Timeout")));
    }

    @Test
    void shouldAllowFrontendOriginViaCors() throws Exception {
        mockMvc.perform(get("/data-collections/messages").header("Origin", "http://localhost:5173"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"));
    }

    @Test
    void shouldAllowPreflightRequests() throws Exception {
        mockMvc.perform(options("/data-collections/messages")
                        .header("Origin", "http://localhost:5173")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"))
                .andExpect(header().string("Access-Control-Allow-Methods", containsString("GET")));
    }

    @Test
    void shouldReturnIntradayDailyCounts() throws Exception {
        mockMvc.perform(get("/data-collections/intraday-daily-counts"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].date", is("2024-11-03")))
                .andExpect(jsonPath("$[0].totalRecords", is(240)))
                .andExpect(jsonPath("$[1].date", is("2024-11-02")))
                .andExpect(jsonPath("$[1].totalRecords", is(180)));
    }

    private List<PythonDataCollectionClient.PythonMessage> sampleMessages() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        return List.of(
                new PythonDataCollectionClient.PythonMessage(
                        "evt-001",
                        "google_finance_price",
                        "SUCCESS",
                        "Preços intraday capturados para 2 tickers.",
                        "cotacao_intraday.cotacao_bovespa",
                        now,
                        Map.of(
                                "tickersSolicitados",
                                List.of("PETR4", "VALE3", "BBAS3"),
                                "cotacoes",
                                List.of(
                                        Map.of("ticker", "PETR4", "valor", 32.1),
                                        Map.of("ticker", "VALE3", "valor", 71.5)),
                                "falhas",
                                Map.of("BBAS3", "Timeout ao consultar fonte"))),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-002",
                        "ingestao-crypto",
                        "WARNING",
                        "Oscilação detectada durante a coleta de preços.",
                        "bronze.cotacoes_crypto",
                        now.minusMinutes(9),
                        Map.of("exchange", "Binance", "paresAfetados", 3)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-003",
                        "ingestao-b3",
                        "ERROR",
                        "Falha ao escrever no BigQuery.",
                        "silver.cotacoes_ajustadas",
                        now.minusMinutes(24),
                        Map.of("stacktraceId", "a1b2c3", "retriesExecutados", 2)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-004",
                        "ingestao-news",
                        "INFO",
                        "Coleta agendada iniciada.",
                        "raw.noticias",
                        now.minusMinutes(37),
                        Map.of("fonte", "B3", "artigosCarregados", 15)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-005",
                        "ingestao-crypto",
                        "CRITICAL",
                        "Falha geral na ingestão de ordens.",
                        "gold.ordens_criticas",
                        now.minusMinutes(51),
                        Map.of("acaoRecomendada", "Acionar suporte")));
    }

    private List<IntradayDailyCount> sampleIntradayCounts() {
        return List.of(
                new IntradayDailyCount(java.time.LocalDate.parse("2024-11-03"), 240L),
                new IntradayDailyCount(java.time.LocalDate.parse("2024-11-02"), 180L));
    }
}
