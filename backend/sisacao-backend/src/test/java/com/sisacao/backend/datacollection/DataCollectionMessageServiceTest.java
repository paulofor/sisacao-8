package com.sisacao.backend.datacollection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
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
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty());

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
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty());

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
                new DataCollectionMessageService(pythonClient, Optional.of(bigQueryClient), Optional.empty());

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
                        pythonClient, Optional.of(bigQueryClient), Optional.of(metricsClient));

        List<IntradayDailyCount> result = service.fetchIntradayDailyCounts();

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().totalRecords()).isEqualTo(120L);
    }

    @Test
    void shouldReturnEmptyCountsWhenMetricsClientMissing() {
        DataCollectionMessageService service =
                new DataCollectionMessageService(pythonClient, Optional.empty(), Optional.empty());

        List<IntradayDailyCount> result = service.fetchIntradayDailyCounts();

        assertThat(result).isEmpty();
        verifyNoInteractions(pythonClient);
    }
}
