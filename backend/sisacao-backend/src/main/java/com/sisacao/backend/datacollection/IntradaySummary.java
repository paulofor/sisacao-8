package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
import java.time.OffsetDateTime;
import java.util.List;

@JsonInclude(Include.NON_NULL)
public record IntradaySummary(
        OffsetDateTime updatedAt,
        int totalTickers,
        int successfulTickers,
        int failedTickers,
        List<IntradayTickerSummary> tickers) {

    public static IntradaySummary empty() {
        return new IntradaySummary(null, 0, 0, 0, List.of());
    }
}
