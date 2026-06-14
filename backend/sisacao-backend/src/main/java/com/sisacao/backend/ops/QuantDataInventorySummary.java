package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record QuantDataInventorySummary(
        Long activeTickers,
        Long totalTickers,
        Long dailyTickers,
        Long intradayTickers,
        LocalDate firstAvailableDate,
        LocalDate lastAvailableDate,
        Long dailyCandles,
        Long intradayCandles,
        Double validDataPct,
        OffsetDateTime lastUpdate) {}
