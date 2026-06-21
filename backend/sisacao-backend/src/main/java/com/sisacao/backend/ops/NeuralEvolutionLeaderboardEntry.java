package com.sisacao.backend.ops;

import java.time.OffsetDateTime;

public record NeuralEvolutionLeaderboardEntry(
        String candidateId,
        String evolutionRunId,
        String strategy,
        String evolutionStatus,
        String modelId,
        String modelVersion,
        String candidateSource,
        String datasetSnapshot,
        String featureVersion,
        String labelVersion,
        String architectureJson,
        String hyperparametersJson,
        Double scoreTotal,
        Double scoreDirectionalPrecision,
        Double scoreCoverage,
        Double scoreGeneralization,
        Double scoreStability,
        Double scoreCostPenalty,
        String decision,
        String decisionReasonsJson,
        Long rankInRun,
        OffsetDateTime createdAt) {
}
