package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/ops")
@ConditionalOnProperty(prefix = "sisacao.ops.bigquery", name = "enabled", havingValue = "true")
public class OpsController {

    private final OpsService opsService;

    public OpsController(OpsService opsService) {
        this.opsService = opsService;
    }

    @GetMapping("/overview")
    public OpsOverview getOverview() {
        return opsService.getOverview();
    }

    @GetMapping("/pipeline")
    public List<PipelineJobStatus> getPipelineStatus() {
        return opsService.getPipelineStatus();
    }

    @GetMapping("/dq/latest")
    public List<DqCheck> getLatestDqChecks() {
        return opsService.getLatestDqChecks();
    }

    @GetMapping("/neural/training-data/allocation")
    public List<NeuralTrainingDataAllocation> getNeuralTrainingDataAllocation() {
        return opsService.getNeuralTrainingDataAllocation();
    }

    @GetMapping("/neural/training-runs")
    public List<NeuralTrainingRun> getNeuralTrainingRuns() {
        return opsService.getNeuralTrainingRuns();
    }

    @GetMapping("/neural/evolution/leaderboard")
    public List<NeuralEvolutionLeaderboardEntry> getNeuralEvolutionLeaderboard() {
        return opsService.getNeuralEvolutionLeaderboard();
    }

    @GetMapping("/neural/gate-decisions")
    public List<NeuralGateDecisionAttempt> getNeuralGateDecisions() {
        return opsService.getNeuralGateDecisions();
    }

    @GetMapping("/neural/champion-monitoring")
    public NeuralChampionMonitoring getNeuralChampionMonitoring() {
        return opsService.getNeuralChampionMonitoring();
    }

    @GetMapping("/quant/inventory-summary")
    public QuantDataInventorySummary getQuantDataInventorySummary() {
        return opsService.getQuantDataInventorySummary();
    }

    @GetMapping("/quant/ticker-coverage")
    public List<QuantTickerCoverage> getQuantTickerCoverage(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantTickerCoverage(limit);
    }

    @GetMapping("/quant/data-quality-incidents")
    public List<QuantDataQualityIncident> getQuantDataQualityIncidents(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantDataQualityIncidents(limit);
    }

    @GetMapping("/quant/strategies")
    public List<QuantBaselineStrategy> getQuantBaselineStrategies() {
        return opsService.getQuantBaselineStrategies();
    }

    @GetMapping("/quant/strategies/alerts")
    public List<QuantStrategyDetailAlert> getQuantStrategyDetailAlerts() {
        return opsService.getQuantStrategyDetailAlerts();
    }

    @GetMapping("/quant/ranking/daily")
    public List<QuantRankingDailyEntry> getQuantRankingDaily(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantRankingDaily(limit);
    }

    @GetMapping("/quant/ranking/performance")
    public List<QuantRankingPerformance> getQuantRankingPerformance() {
        return opsService.getQuantRankingPerformance();
    }

    @GetMapping("/quant/market-regime")
    public List<QuantMarketRegime> getQuantMarketRegime(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantMarketRegime(limit);
    }

    @GetMapping("/quant/exposure")
    public List<QuantExposureRecommendation> getQuantExposureRecommendations(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantExposureRecommendations(limit);
    }

    @GetMapping("/quant/strategy-regime-performance")
    public List<QuantStrategyRegimePerformance> getQuantStrategyRegimePerformance() {
        return opsService.getQuantStrategyRegimePerformance();
    }

    @GetMapping("/quant/filter-effectiveness")
    public List<QuantFilterEffectiveness> getQuantFilterEffectiveness() {
        return opsService.getQuantFilterEffectiveness();
    }

    @GetMapping("/quant/paper-trading")
    public QuantPaperTradingPayload getQuantPaperTrading(@RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getQuantPaperTrading(limit);
    }

    @GetMapping("/quant/strategies/{strategyId}")
    public QuantBaselineStrategy getQuantBaselineStrategy(@PathVariable String strategyId) {
        return opsService.getQuantBaselineStrategy(strategyId);
    }

    @GetMapping("/incidents/open")
    public List<OpsIncident> getOpenIncidents() {
        return opsService.getOpenIncidents();
    }

    @GetMapping("/signals/next")
    public List<Signal> getNextSignals() {
        return opsService.getNextSignals();
    }

    @GetMapping("/signals/by-date")
    public List<SignalByDateEntry> getSignalsByDate(@RequestParam("date") String date) {
        LocalDate selectedDate = parseDate(date, "date");
        return opsService.getSignalsByDate(selectedDate);
    }

    @GetMapping("/backtest/trades")
    public List<OpsBacktestTrade> getLatestBacktestTrades(
            @RequestParam(name = "limit", required = false) Integer limit) {
        return opsService.getLatestBacktestTrades(limit);
    }

    @GetMapping("/signals/history")
    public List<SignalHistoryEntry> getSignalsHistory(
            @RequestParam("from") String from,
            @RequestParam("to") String to,
            @RequestParam(name = "limit", required = false) Integer limit) {
        LocalDate fromDate = parseDate(from, "from");
        LocalDate toDate = parseDate(to, "to");
        return opsService.getSignalsHistory(fromDate, toDate, limit);
    }

    private LocalDate parseDate(String raw, String paramName) {
        if (raw == null || raw.isBlank()) {
            throw new OpsValidationException("O parâmetro '" + paramName + "' é obrigatório e deve estar no formato YYYY-MM-DD.");
        }
        try {
            return LocalDate.parse(raw.trim());
        } catch (DateTimeParseException ex) {
            throw new OpsValidationException(
                    "Não foi possível interpretar o parâmetro '" + paramName + "'. Use o formato YYYY-MM-DD.");
        }
    }
}
