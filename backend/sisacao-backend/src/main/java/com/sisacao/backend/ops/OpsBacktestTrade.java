package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record OpsBacktestTrade(
        LocalDate dateRef,
        String ticker,
        String side,
        Double entry,
        Double exit,
        String outcome,
        Double pnlPct,
        LocalDate entryDate,
        Double entryPrice,
        LocalDate exitDate,
        Double exitPrice,
        Long daysInTrade,
        Double entryLimitPrice,
        Double entrySignalScore,
        OffsetDateTime createdAt) {}
