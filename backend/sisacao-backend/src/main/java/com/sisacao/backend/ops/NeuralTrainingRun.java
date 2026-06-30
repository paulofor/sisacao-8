package com.sisacao.backend.ops;

import java.time.OffsetDateTime;

public record NeuralTrainingRun(
        String modelId,
        String modelVersion,
        String status,
        String featureVersion,
        String labelVersion,
        String trainingDatasetSnapshot,
        String artifactUri,
        Long featureColumnsCount,
        Long labelClassesCount,
        Double directionalPrecision,
        Double coverage,
        Double validationAccuracy,
        Double testAccuracy,
        String metricsJson,
        String confusionMatrixJson,
        OffsetDateTime trainedAt,
        OffsetDateTime createdAt,
        String notes,
        Long totalRuns,
        Long candidateRuns,
        Long approvedRuns,
        Long rejectedRuns,
        Long activeTrainingRuns) {
}
