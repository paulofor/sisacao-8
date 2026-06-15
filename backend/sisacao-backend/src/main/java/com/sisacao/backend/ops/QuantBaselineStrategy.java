package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantBaselineStrategy(
        String strategyId,
        String strategyFamily,
        String strategyVersion,
        String hypothesis,
        String configuredStatus,
        Long generatedSignals,
        Long signalDays,
        LocalDate lastSignalDate,
        Long trades,
        Double expectancyNetPct,
        Double profitFactor,
        Double maxDrawdownPct,
        Double robustnessScore,
        String computedStatus) {}
