package com.sisacao.backend.ops;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;

import com.sisacao.backend.ops.bigquery.BigQueryOpsClient;
import com.sisacao.backend.ops.bigquery.OpsBigQueryProperties;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OpsServiceTest {

    @Mock
    private BigQueryOpsClient bigQueryOpsClient;

    @Mock
    private OpsBigQueryProperties properties;

    @InjectMocks
    private OpsService opsService;


    @Test
    void shouldFetchSignalsByDate() {
        LocalDate date = LocalDate.parse("2024-10-31");
        when(bigQueryOpsClient.fetchSignalsByDate(date)).thenReturn(List.of());

        opsService.getSignalsByDate(date);

        org.mockito.Mockito.verify(bigQueryOpsClient).fetchSignalsByDate(date);
    }

    @Test
    void shouldFetchNeuralGateDecisions() {
        when(bigQueryOpsClient.fetchNeuralGateDecisions()).thenReturn(List.of());

        opsService.getNeuralGateDecisions();

        org.mockito.Mockito.verify(bigQueryOpsClient).fetchNeuralGateDecisions();
    }

    @Test
    void shouldRejectNullSignalsByDate() {
        assertThatThrownBy(() -> opsService.getSignalsByDate(null))
                .isInstanceOf(OpsValidationException.class)
                .hasMessageContaining("date");
    }

    @Test
    void shouldCapBacktestLimitToTwoHundred() {
        when(bigQueryOpsClient.fetchLatestBacktestTrades(anyInt())).thenReturn(List.of());

        opsService.getLatestBacktestTrades(500);

        org.mockito.Mockito.verify(bigQueryOpsClient).fetchLatestBacktestTrades(200);
    }

    @Test
    void shouldUseDefaultBacktestLimitWhenNull() {
        when(bigQueryOpsClient.fetchLatestBacktestTrades(anyInt())).thenReturn(List.of());

        opsService.getLatestBacktestTrades(null);

        org.mockito.Mockito.verify(bigQueryOpsClient).fetchLatestBacktestTrades(50);
    }
}
