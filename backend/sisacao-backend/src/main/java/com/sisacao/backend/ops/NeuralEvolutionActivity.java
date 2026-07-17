package com.sisacao.backend.ops;

public record NeuralEvolutionActivity(
        String activityDate,
        String strategy,
        long runsCount,
        long completedRunsCount,
        long failedRunsCount,
        long candidatesCount,
        long trainedCount,
        long gateDecisionsCount,
        long approvedGateDecisionsCount) {
}
