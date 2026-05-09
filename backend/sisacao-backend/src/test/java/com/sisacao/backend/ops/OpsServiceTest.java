package com.sisacao.backend.ops;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;

import com.sisacao.backend.ops.bigquery.BigQueryOpsClient;
import com.sisacao.backend.ops.bigquery.OpsBigQueryProperties;
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
    void shouldReturnEmptyListWhenBacktestQueryFails() {
        when(bigQueryOpsClient.fetchLatestBacktestTrades(anyInt()))
                .thenThrow(new OpsDataAccessException("Falha ao consultar backtest"));

        List<OpsBacktestTrade> result = opsService.getLatestBacktestTrades(50);

        assertTrue(result.isEmpty());
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

        List<OpsBacktestTrade> result = opsService.getLatestBacktestTrades(null);

        org.mockito.Mockito.verify(bigQueryOpsClient).fetchLatestBacktestTrades(50);
        assertEquals(0, result.size());
    }
}
