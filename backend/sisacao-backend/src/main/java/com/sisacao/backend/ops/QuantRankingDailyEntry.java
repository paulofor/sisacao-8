package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantRankingDailyEntry(
        String rankingModelId,
        String rankingModelVersion,
        LocalDate referenceDate,
        Long rankingPosition,
        Long rankingDecile,
        String ticker,
        Double finalScore,
        Double relativeStrengthFactor,
        Double shortMomentumFactor,
        Double relativeVolumeFactor,
        Double volatilityFactor,
        Double meanDistanceFactor,
        Double candleQualityFactor,
        Double indexRegimeFactor,
        Double currentPrice,
        Double liquidityValue,
        Double estimatedRisk,
        String marketRegimeLabel,
        Double forwardReturn5d,
        String factorBreakdownJson,
        String actionSuggestion,
        String confidenceLabel) {
}
