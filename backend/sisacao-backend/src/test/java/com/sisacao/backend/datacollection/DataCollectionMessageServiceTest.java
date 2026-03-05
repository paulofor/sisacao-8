package com.sisacao.backend.datacollection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class DataCollectionMessageServiceTest {

    private final PythonDataCollectionClient pythonClient = mock(PythonDataCollectionClient.class);
    private final BigQueryCollectionMessageClient bigQueryClient = mock(BigQueryCollectionMessageClient.class);
    private final BigQueryIntradayMetricsClient metricsClient = mock(BigQueryIntradayMetricsClient.class);
    private final DataCollectionBigQueryProperties properties = new DataCollectionBigQueryProperties();

    @Test
    void shouldUseBigQueryClientWhenItReturnsMessages() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        List<PythonDataCollectionClient.PythonMessage> bigQueryMessages =
                List.of(new PythonDataCollectionClient.PythonMessage(
                        "evt-123",
                        "google_finance_price",
                        "SUCCESS",
                        "Resumo vindo do BigQuery",
                        "cotacao_intraday.cotacao_bovespa",
                        now,
                        Map.of("fonte", "bigquery")));

        when(bigQueryClient.fetchMessages()).thenReturn(bigQueryMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty(), properties);

        List<DataCollectionMessage> result = service.findMessages(null, null, null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).collector()).isEqualTo("google_finance_price");
        verifyNoInteractions(pythonClient);
    }

    @Test
    void shouldFallbackToPythonWhenBigQueryThrows() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        List<PythonDataCollectionClient.PythonMessage> pythonMessages =
                List.of(new PythonDataCollectionClient.PythonMessage(
                        "evt-900",
                        "get_stock_data",
                        "WARNING",
                        "Resumo Python",
                        "cotacao_intraday.cotacao_fechamento_diario",
                        now,
                        Map.of("fonte", "python")));

        when(bigQueryClient.fetchMessages()).thenThrow(new IllegalStateException("boom"));
        when(pythonClient.fetchMessages()).thenReturn(pythonMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty(), properties);

        List<DataCollectionMessage> result = service.findMessages(null, null, null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).collector()).isEqualTo("get_stock_data");
    }

    @Test
    void shouldFallbackToPythonWhenBigQueryReturnsEmpty() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        List<PythonDataCollectionClient.PythonMessage> pythonMessages =
                List.of(new PythonDataCollectionClient.PythonMessage(
                        "evt-777",
                        "ingestao-news",
                        "INFO",
                        "Resumo Python",
                        "raw.noticias",
                        now,
                        Map.of("fonte", "python")));

        when(bigQueryClient.fetchMessages()).thenReturn(List.of());
        when(pythonClient.fetchMessages()).thenReturn(pythonMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty(), properties);

        List<DataCollectionMessage> result = service.findMessages(null, null, null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).collector()).isEqualTo("ingestao-news");
    }

    @Test
    void shouldReturnIntradayCountsFromMetricsClient() {
        List<IntradayDailyCount> counts =
                List.of(new IntradayDailyCount(java.time.LocalDate.parse("2024-11-01"), 120L));
        when(metricsClient.fetchDailyCounts()).thenReturn(counts);

        DataCollectionMessageService service =
                new DataCollectionMessageService(
                        pythonClient, Optional.of(bigQueryClient), Optional.of(metricsClient), properties);

        List<IntradayDailyCount> result = service.fetchIntradayDailyCounts();

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().totalRecords()).isEqualTo(120L);
    }

    @Test
    void shouldBuildIntradayCountsFromPythonMessagesWhenMetricsUnavailable() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        Map<String, Object> metadata = Map.of(
                "cotacoes",
                List.of(
                        Map.of("ticker", "PETR4", "valor", 32.5),
                        Map.of("ticker", "VALE3", "valor", 68.1)
                ));
        List<PythonDataCollectionClient.PythonMessage> pythonMessages =
                List.of(new PythonDataCollectionClient.PythonMessage(
                        "evt-555",
                        "google_finance_price",
                        "SUCCESS",
                        "Resumo fallback",
                        "cotacao_intraday.cotacao_bovespa",
                        now,
                        metadata));

        when(pythonClient.fetchMessages()).thenReturn(pythonMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.empty(), Optional.empty(), properties);

        List<IntradayDailyCount> result = service.fetchIntradayDailyCounts();

        assertThat(result).hasSize(1);
        IntradayDailyCount count = result.getFirst();
        assertThat(count.totalRecords()).isEqualTo(2L);
        assertThat(count.date()).isEqualTo(now.toLocalDate());
        verify(pythonClient).fetchMessages();
    }

    @Test
    void shouldReturnDailyCountsFromMetricsClient() {
        List<IntradayDailyCount> counts =
                List.of(new IntradayDailyCount(java.time.LocalDate.parse("2024-11-01"), 52L));
        when(metricsClient.fetchDailyTableCounts()).thenReturn(counts);

        DataCollectionMessageService service =
                new DataCollectionMessageService(
                        pythonClient, Optional.of(bigQueryClient), Optional.of(metricsClient), properties);

        List<IntradayDailyCount> result = service.fetchDailyTableCounts();

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().totalRecords()).isEqualTo(52L);
    }

    @Test
    void shouldLimitDailyCountsToLatestTradingSessionsFromPythonMessages() {
        properties.setDailyDays(5);
        List<PythonDataCollectionClient.PythonMessage> pythonMessages = List.of(
                new PythonDataCollectionClient.PythonMessage(
                        "evt-100",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-03-05T20:00:00Z"),
                        Map.of("registrosInseridos", 10)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-101",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-03-04T20:00:00Z"),
                        Map.of("registrosInseridos", 12)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-102",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-03-03T20:00:00Z"),
                        Map.of("registrosInseridos", 8)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-103",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-03-02T20:00:00Z"),
                        Map.of("registrosInseridos", 9)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-104",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-02-27T20:00:00Z"),
                        Map.of("registrosInseridos", 11)),
                new PythonDataCollectionClient.PythonMessage(
                        "evt-105",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        OffsetDateTime.parse("2026-02-26T20:00:00Z"),
                        Map.of("registrosInseridos", 7)));

        when(pythonClient.fetchMessages()).thenReturn(pythonMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.empty(), Optional.empty(), properties);

        List<IntradayDailyCount> result = service.fetchDailyTableCounts();

        assertThat(result).hasSize(5);
        assertThat(result)
                .extracting(IntradayDailyCount::date)
                .containsExactly(
                        java.time.LocalDate.parse("2026-03-05"),
                        java.time.LocalDate.parse("2026-03-04"),
                        java.time.LocalDate.parse("2026-03-03"),
                        java.time.LocalDate.parse("2026-03-02"),
                        java.time.LocalDate.parse("2026-02-27"));
        verify(pythonClient).fetchMessages();
    }

    @Test
    void shouldBuildDailyCountsFromPythonMessagesWhenMetricsUnavailable() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        Map<String, Object> metadata = Map.of(
                "registrosInseridos", 23,
                "linhasProcessadas", 23);
        List<PythonDataCollectionClient.PythonMessage> pythonMessages =
                List.of(new PythonDataCollectionClient.PythonMessage(
                        "evt-888",
                        "get_stock_data",
                        "SUCCESS",
                        "Resumo fallback diário",
                        "cotacao_intraday.cotacao_ohlcv_diario",
                        now,
                        metadata));

        when(pythonClient.fetchMessages()).thenReturn(pythonMessages);

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.empty(), Optional.empty(), properties);

        List<IntradayDailyCount> result = service.fetchDailyTableCounts();

        assertThat(result).hasSize(1);
        IntradayDailyCount count = result.getFirst();
        assertThat(count.totalRecords()).isEqualTo(23L);
        assertThat(count.date()).isEqualTo(now.toLocalDate());
        verify(pythonClient).fetchMessages();
    }

    @Test
    void shouldReturnEmptyCountsWhenMetricsClientMissing() {
        when(pythonClient.fetchMessages()).thenReturn(List.of());

        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.empty(), Optional.empty(), properties);

        List<IntradayDailyCount> result = service.fetchIntradayDailyCounts();

        assertThat(result).isEmpty();
        verify(pythonClient).fetchMessages();
    }
}
