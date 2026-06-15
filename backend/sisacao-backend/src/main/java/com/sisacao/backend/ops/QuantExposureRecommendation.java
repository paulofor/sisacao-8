package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantExposureRecommendation(
        String policyId,
        String policyVersion,
        LocalDate referenceDate,
        String marketRegime,
        Double marketReturn5d,
        Double marketReturn20d,
        Double realizedVolatility20d,
        Double volatilityPercentile,
        Double pctAboveSma20,
        Double pctAboveSma50,
        Double aggregateRelativeVolume,
        String exposureAction,
        Double maxExposurePct,
        Long maxTrades,
        Double riskPerTradePct,
        Double dailyLossLimitPct,
        String recommendationReason) {
}
