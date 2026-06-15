package com.sisacao.backend.ops;

public record QuantRankingPerformance(
        String rankingModelId,
        String rankingModelVersion,
        Long topN,
        Long portfolioDays,
        Double avgTopNReturn5d,
        Double volatilityTopNReturn5d,
        Double positiveDayRate,
        Double avgExcessVsRandom5d,
        Double decileReturnCorrelation,
        Double topDecileReturn5d,
        Double bottomDecileReturn5d,
        Double topMinusBottomDecileReturn5d,
        String rankingStatus) {
}
