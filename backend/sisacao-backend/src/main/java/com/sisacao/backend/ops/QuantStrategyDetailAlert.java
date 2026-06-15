package com.sisacao.backend.ops;

import java.util.List;

public record QuantStrategyDetailAlert(
        String strategyId,
        String strategyVersion,
        Long generatedSignals,
        Long trades,
        Double expectancyNetPct,
        Double profitFactor,
        Double maxDrawdownPct,
        List<String> alerts) {}
