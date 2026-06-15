package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantMarketRegime(
        LocalDate referenceDate,
        Long eligibleTickers,
        Double marketReturn5d,
        Double marketReturn20d,
        Double realizedVolatility20d,
        Double avgMarketVolatility60d,
        Double volatilityPercentile,
        Double pctAboveSma20,
        Double pctAboveSma50,
        Double pctPositive5d,
        Double aggregateFinancialVolume,
        Double aggregateRelativeVolume,
        String marketRegime,
        String regimeIndicatorsJson) {
}
