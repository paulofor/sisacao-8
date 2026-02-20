package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record OpsOverview(
        OffsetDateTime asOf,
        LocalDate lastTradingDay,
        LocalDate nextTradingDay,
        String pipelineHealth,
        String dqHealth,
        boolean signalsReady,
        long signalsCount,
        OffsetDateTime lastSignalsGeneratedAt) {

    public static OpsOverview empty() {
        return new OpsOverview(
                OffsetDateTime.now(),
                null,
                null,
                "UNKNOWN",
                "UNKNOWN",
                false,
                0L,
                null);
    }
}
