package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantPaperTradingDashboard(
        LocalDate referenceDate,
        Long openOrders,
        Long closedOrders,
        Long totalOrders,
        Double dailyPnlPct,
        Double cumulativePnlPct,
        Double avgSlippagePct,
        Double executionRate,
        Double avgAbsDivergencePct,
        String adherenceStatus) {}
