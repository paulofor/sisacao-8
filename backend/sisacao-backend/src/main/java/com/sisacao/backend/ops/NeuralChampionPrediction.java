package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record NeuralChampionPrediction(
        LocalDate referenceDate,
        LocalDate validFor,
        String ticker,
        String suggestedAction,
        Double confidence,
        Double probUp,
        Double probDown,
        Double probNeutral,
        Double close,
        Double financialVolume,
        String jobRunId,
        OffsetDateTime createdAt) {
}
