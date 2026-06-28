package com.sisacao.backend.ops;

import java.time.OffsetDateTime;

public record NeuralGateDecisionAttempt(
        String decisionId,
        String protocolVersion,
        String datasetSnapshot,
        String candidateFamilyHash,
        String gateName,
        String decisionStatus,
        Boolean passed,
        String failedCriteria,
        String metricsJson,
        String gateEngineVersion,
        OffsetDateTime decidedAt,
        Long folds,
        Long seeds,
        Long positiveFolds,
        Double positiveFoldRatio,
        Double medianDeltaExpectancyVsChampion,
        Double medianExpectancyNet,
        Double maxDrawdown,
        Long totalTrades,
        Boolean stableAcrossSeeds) {
}
