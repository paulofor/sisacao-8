package com.sisacao.backend.ops;

import java.util.List;

public record NeuralChampionMonitoring(
        NeuralTrainingRun champion,
        NeuralGateDecisionAttempt gateDecision,
        List<NeuralChampionPrediction> predictions,
        List<SignalHistoryEntry> signals) {
}
