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
        OffsetDateTime createdAt) {}
