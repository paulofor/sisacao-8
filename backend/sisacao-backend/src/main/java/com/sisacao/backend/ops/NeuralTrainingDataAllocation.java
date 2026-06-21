package com.sisacao.backend.ops;

import java.time.LocalDate;

public record NeuralTrainingDataAllocation(
        String featureVersion,
        String labelVersion,
        String datasetSplit,
        Long rowsCount,
        Long tickersCount,
        LocalDate minReferenceDate,
        LocalDate maxReferenceDate,
        Long upCount,
        Long downCount,
        Long neutralCount,
        Double upRatio,
        Double downRatio,
        Double neutralRatio,
        Long missingOhlcvCount,
        Long zeroVolumeCount,
        Long suspiciousCandleCount,
        Long targetHitCount,
        Long stopHitCount) {
}
