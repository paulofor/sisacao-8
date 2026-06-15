package com.sisacao.backend.ops;

public record QuantStrategyRegimePerformance(
        String strategyId,
        String strategyVersion,
        String marketRegime,
        Long trades,
        Double expectancyNetPct,
        Double winRate,
        Double profitFactor,
        Double totalNetPnlPct,
        String regimeEffectStatus) {
}
