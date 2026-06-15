package com.sisacao.backend.ops;

public record QuantFilterEffectiveness(
        String strategyId,
        String strategyVersion,
        Long originalTrades,
        Long tradesAfterFilter,
        Double originalExpectancyNetPct,
        Double filteredExpectancyNetPct,
        Double blockedExpectancyNetPct,
        Double blockedTradePct,
        Double originalTotalNetPnlPct,
        Double exposureAdjustedTotalNetPnlPct,
        String filterEffectivenessStatus) {
}
