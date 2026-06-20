package com.sisacao.backend.ops.bigquery;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryException;
import com.google.cloud.bigquery.FieldValue;
import com.google.cloud.bigquery.FieldValueList;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.QueryParameterValue;
import com.google.cloud.bigquery.TableResult;
import com.sisacao.backend.ops.DqCheck;
import com.sisacao.backend.ops.OpsDataAccessException;
import com.sisacao.backend.ops.OpsBacktestTrade;
import com.sisacao.backend.ops.OpsIncident;
import com.sisacao.backend.ops.NeuralTrainingDataAllocation;
import com.sisacao.backend.ops.NeuralTrainingRun;
import com.sisacao.backend.ops.OpsOverview;
import com.sisacao.backend.ops.PipelineJobStatus;
import com.sisacao.backend.ops.QuantDataInventorySummary;
import com.sisacao.backend.ops.QuantDataQualityIncident;
import com.sisacao.backend.ops.QuantBaselineStrategy;
import com.sisacao.backend.ops.QuantStrategyDetailAlert;
import com.sisacao.backend.ops.QuantRankingDailyEntry;
import com.sisacao.backend.ops.QuantRankingPerformance;
import com.sisacao.backend.ops.QuantMarketRegime;
import com.sisacao.backend.ops.QuantExposureRecommendation;
import com.sisacao.backend.ops.QuantStrategyRegimePerformance;
import com.sisacao.backend.ops.QuantFilterEffectiveness;
import com.sisacao.backend.ops.QuantOperationalDiaryEvent;
import com.sisacao.backend.ops.QuantPaperTradingDashboard;
import com.sisacao.backend.ops.QuantPaperTradingOrder;
import com.sisacao.backend.ops.QuantPaperTradingPayload;
import com.sisacao.backend.ops.QuantTickerCoverage;
import com.sisacao.backend.ops.Signal;
import com.sisacao.backend.ops.SignalByDateEntry;
import com.sisacao.backend.ops.SignalHistoryEntry;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

public class BigQueryOpsClient {

    private final BigQuery bigQuery;
    private final OpsBigQueryProperties properties;

    public BigQueryOpsClient(BigQuery bigQuery, OpsBigQueryProperties properties) {
        this.bigQuery = bigQuery;
        this.properties = properties;
    }

    public OpsOverview fetchOverview() {
        String sql = "SELECT * FROM " + qualifiedView(properties.getOverviewView()) + " LIMIT 1";
        TableResult result = runQuery(sql, Map.of());
        for (FieldValueList row : result.iterateAll()) {
            return toOverview(row);
        }
        return OpsOverview.empty();
    }

    public List<PipelineJobStatus> fetchPipelineStatus() {
        String sql = "SELECT * FROM " + qualifiedView(properties.getPipelineView()) + " ORDER BY jobName";
        TableResult result = runQuery(sql, Map.of());
        List<PipelineJobStatus> jobs = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            jobs.add(toPipelineJobStatus(row));
        }
        return Collections.unmodifiableList(jobs);
    }

    public List<DqCheck> fetchLatestDqChecks() {
        String sql = "SELECT * FROM " + qualifiedView(properties.getDqLatestView()) + " ORDER BY createdAt DESC";
        TableResult result = runQuery(sql, Map.of());
        List<DqCheck> checks = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            checks.add(toDqCheck(row));
        }
        return Collections.unmodifiableList(checks);
    }

    public List<OpsIncident> fetchOpenIncidents() {
        String sql = "SELECT * FROM " + qualifiedView(properties.getIncidentsView()) + " ORDER BY createdAt DESC";
        TableResult result = runQuery(sql, Map.of());
        List<OpsIncident> incidents = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            incidents.add(toIncident(row));
        }
        return Collections.unmodifiableList(incidents);
    }

    public List<NeuralTrainingDataAllocation> fetchNeuralTrainingDataAllocation() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getNeuralTrainingDataAllocationView())
                + " ORDER BY feature_version ASC, label_version ASC, "
                + "CASE dataset_split "
                + "WHEN 'train' THEN 1 "
                + "WHEN 'validation' THEN 2 "
                + "WHEN 'test' THEN 3 "
                + "ELSE 4 END";
        TableResult result = runQuery(sql, Map.of());
        List<NeuralTrainingDataAllocation> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toNeuralTrainingDataAllocation(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<NeuralTrainingRun> fetchNeuralTrainingRuns() {
        String sql = "SELECT "
                + "model_id, model_version, status, feature_version, label_version, "
                + "training_dataset_snapshot, artifact_uri, "
                + "ARRAY_LENGTH(feature_columns) AS feature_columns_count, "
                + "ARRAY_LENGTH(label_classes) AS label_classes_count, "
                + "directional_precision, coverage, validation_accuracy, test_accuracy, "
                + "TO_JSON_STRING(metrics_json) AS metrics_json, "
                + "TO_JSON_STRING(confusion_matrix_json) AS confusion_matrix_json, "
                + "trained_at, created_at, notes "
                + "FROM " + qualifiedQuantView(properties.getNeuralModelRegistryTable())
                + " ORDER BY trained_at DESC, created_at DESC LIMIT 100";
        TableResult result = runQuery(sql, Map.of());
        List<NeuralTrainingRun> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toNeuralTrainingRun(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public QuantDataInventorySummary fetchQuantDataInventorySummary() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantInventorySummaryView()) + " LIMIT 1";
        TableResult result = runQuery(sql, Map.of());
        for (FieldValueList row : result.iterateAll()) {
            return toQuantDataInventorySummary(row);
        }
        return new QuantDataInventorySummary(0L, 0L, 0L, 0L, null, null, 0L, 0L, null, null);
    }

    public List<QuantTickerCoverage> fetchQuantTickerCoverage(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantTickerCoverageView())
                + " ORDER BY eligibility_status ASC, coverage_pct DESC, avg_financial_volume DESC LIMIT @limit";
        TableResult result = runQuery(sql, params);
        List<QuantTickerCoverage> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantTickerCoverage(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantDataQualityIncident> fetchQuantDataQualityIncidents(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantDataQualityIncidentsView())
                + " ORDER BY incident_date DESC, severity DESC, ticker ASC LIMIT @limit";
        TableResult result = runQuery(sql, params);
        List<QuantDataQualityIncident> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantDataQualityIncident(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantBaselineStrategy> fetchQuantBaselineStrategies() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantBaselineStatusView())
                + " ORDER BY strategy_family ASC, strategy_id ASC";
        TableResult result = runQuery(sql, Map.of());
        List<QuantBaselineStrategy> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantBaselineStrategy(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public Optional<QuantBaselineStrategy> fetchQuantBaselineStrategy(String strategyId) {
        Map<String, QueryParameterValue> params = Map.of("strategyId", QueryParameterValue.string(strategyId));
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantBaselineStatusView())
                + " WHERE strategy_id = @strategyId LIMIT 1";
        TableResult result = runQuery(sql, params);
        for (FieldValueList row : result.iterateAll()) {
            return Optional.of(toQuantBaselineStrategy(row));
        }
        return Optional.empty();
    }

    public List<QuantStrategyDetailAlert> fetchQuantStrategyDetailAlerts() {
        String sql = "SELECT strategy_id, strategy_version, generated_signals, trades, expectancy_net_pct, "
                + "profit_factor, max_drawdown_pct, ARRAY_TO_STRING(alerts, '|') AS alerts_text FROM "
                + qualifiedQuantView(properties.getQuantStrategyDetailAlertsView())
                + " ORDER BY strategy_id ASC, strategy_version ASC";
        TableResult result = runQuery(sql, Map.of());
        List<QuantStrategyDetailAlert> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantStrategyDetailAlert(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantRankingDailyEntry> fetchQuantRankingDaily(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        String rankingView = qualifiedQuantView(properties.getQuantRankingDailyView());
        String sql = "WITH ranking AS ("
                + " SELECT ranking_model_id, ranking_model_version, reference_date, ranking_position, "
                + "ranking_decile, ticker, final_score, relative_strength_factor, short_momentum_factor, "
                + "relative_volume_factor, volatility_factor, mean_distance_factor, candle_quality_factor, "
                + "index_regime_factor, current_price, liquidity_value, estimated_risk, market_regime_label, "
                + "forward_return_5d, factor_breakdown_json, action_suggestion, confidence_label FROM " + rankingView
                + "), latest AS (SELECT MAX(reference_date) AS reference_date FROM ranking)"
                + " SELECT ranking.* FROM ranking INNER JOIN latest USING (reference_date)"
                + " ORDER BY ranking_model_id ASC, ranking_position ASC LIMIT @limit";
        TableResult result = runQuery(sql, params);
        List<QuantRankingDailyEntry> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantRankingDailyEntry(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantRankingPerformance> fetchQuantRankingPerformance() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantRankingPerformanceView())
                + " ORDER BY ranking_model_id ASC, top_n ASC";
        TableResult result = runQuery(sql, Map.of());
        List<QuantRankingPerformance> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantRankingPerformance(row));
        }
        return Collections.unmodifiableList(rows);
    }


    public List<QuantMarketRegime> fetchQuantMarketRegime(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantMarketRegimeView())
                + " ORDER BY reference_date DESC LIMIT @limit";
        TableResult result = runQuery(sql, params);
        List<QuantMarketRegime> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantMarketRegime(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantExposureRecommendation> fetchQuantExposureRecommendations(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantExposureRecommendationView())
                + " ORDER BY reference_date DESC LIMIT @limit";
        TableResult result = runQuery(sql, params);
        List<QuantExposureRecommendation> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantExposureRecommendation(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantStrategyRegimePerformance> fetchQuantStrategyRegimePerformance() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantStrategyRegimePerformanceView())
                + " ORDER BY strategy_id ASC, market_regime ASC";
        TableResult result = runQuery(sql, Map.of());
        List<QuantStrategyRegimePerformance> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantStrategyRegimePerformance(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public List<QuantFilterEffectiveness> fetchQuantFilterEffectiveness() {
        String sql = "SELECT * FROM " + qualifiedQuantView(properties.getQuantFilterEffectivenessView())
                + " ORDER BY filter_effectiveness_status ASC, strategy_id ASC";
        TableResult result = runQuery(sql, Map.of());
        List<QuantFilterEffectiveness> rows = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            rows.add(toQuantFilterEffectiveness(row));
        }
        return Collections.unmodifiableList(rows);
    }

    public QuantPaperTradingPayload fetchQuantPaperTrading(int limit) {
        QuantPaperTradingDashboard dashboard = null;
        for (FieldValueList row : runQuery("SELECT * FROM " + qualifiedQuantView(properties.getQuantPaperTradingDashboardView())
                + " ORDER BY reference_date DESC LIMIT 1", Map.of()).iterateAll()) {
            dashboard = toQuantPaperTradingDashboard(row);
        }
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        List<QuantPaperTradingOrder> openOrders = new ArrayList<>();
        for (FieldValueList row : runQuery("SELECT * FROM " + qualifiedQuantView(properties.getQuantPaperTradingOpenOrdersView())
                + " ORDER BY opened_at DESC LIMIT @limit", params).iterateAll()) {
            openOrders.add(toQuantPaperTradingOrder(row));
        }
        List<QuantPaperTradingOrder> closedOrders = new ArrayList<>();
        for (FieldValueList row : runQuery("SELECT * FROM " + qualifiedQuantView(properties.getQuantPaperTradingClosedOrdersView())
                + " ORDER BY closed_at DESC LIMIT @limit", params).iterateAll()) {
            closedOrders.add(toQuantPaperTradingOrder(row));
        }
        List<QuantOperationalDiaryEvent> diary = new ArrayList<>();
        for (FieldValueList row : runQuery("SELECT * FROM " + qualifiedQuantView(properties.getQuantOperationalDiaryView())
                + " ORDER BY event_timestamp DESC LIMIT @limit", params).iterateAll()) {
            diary.add(toQuantOperationalDiaryEvent(row));
        }
        return new QuantPaperTradingPayload(dashboard, Collections.unmodifiableList(openOrders), Collections.unmodifiableList(closedOrders), Collections.unmodifiableList(diary));
    }

    public List<Signal> fetchNextSignals() {
        List<Signal> signals;
        try {
            signals = querySignals("SELECT * FROM " + qualifiedView(properties.getSignalsNextView()), Map.of());
        } catch (OpsDataAccessException ex) {
            signals = List.of();
        }
        if (signals.isEmpty()) {
            signals = querySignals(buildSignalsNextFallbackSql(), Map.of());
        }
        List<Signal> orderedSignals = signals.stream()
                .sorted(Comparator.comparing(
                        Signal::rank,
                        Comparator.nullsLast(Integer::compareTo)))
                .toList();
        return Collections.unmodifiableList(orderedSignals);
    }

    public List<OpsBacktestTrade> fetchLatestBacktestTrades(int limit) {
        Map<String, QueryParameterValue> params = Map.of("limit", QueryParameterValue.int64(limit));
        List<OpsBacktestTrade> trades;
        try {
            trades = queryBacktestTrades(buildBacktestTradesPrimarySql(), params);
        } catch (OpsDataAccessException ex) {
            trades = List.of();
        }
        if (trades.isEmpty()) {
            try {
                trades = queryBacktestTrades(buildBacktestTradesFallbackSql(), params);
            } catch (OpsDataAccessException ex) {
                trades = queryBacktestTrades(buildBacktestTradesLegacyFallbackSql(), params);
            }
        }
        return Collections.unmodifiableList(trades);
    }

    private List<OpsBacktestTrade> queryBacktestTrades(String sql, Map<String, QueryParameterValue> params) {
        TableResult result = runQuery(sql, params);
        List<OpsBacktestTrade> trades = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            trades.add(new OpsBacktestTrade(
                    getDate(row, "dateRef", "date_ref"),
                    getString(row, "ticker"),
                    getString(row, "side"),
                    getDouble(row, "entry"),
                    getDouble(row, "exit"),
                    getString(row, "outcome"),
                    getDouble(row, "pnlPct", "pnl_pct"),
                    getDate(row, "entryDate", "entry_date", "trade_entry_date"),
                    getDouble(row, "entryPrice", "entry_price", "trade_entry_price", "entry"),
                    getDate(row, "exitDate", "exit_date", "trade_exit_date"),
                    getDouble(row, "exitPrice", "exit_price", "trade_exit_price", "exit"),
                    getLong(row, "daysInTrade", "days_in_trade", "holding_days", "days"),
                    getDouble(row, "entryLimitPrice", "entry_limit_price", "limit_price", "trigger_price"),
                    getDouble(row, "entrySignalScore", "entry_signal_score", "signal_score", "score"),
                    getTimestamp(row, "createdAt", "created_at")));
        }
        return trades;
    }

    public List<SignalByDateEntry> fetchSignalsByDate(LocalDate date) {
        Map<String, QueryParameterValue> params = Map.of("date", QueryParameterValue.date(date.toString()));
        TableResult result = runQuery(buildSignalsByDateSql(), params);
        List<SignalByDateEntry> signals = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            signals.add(toSignalByDate(row));
        }
        List<SignalByDateEntry> orderedSignals = signals.stream()
                .sorted(Comparator.comparing(
                                SignalByDateEntry::rank,
                                Comparator.nullsLast(Integer::compareTo))
                        .thenComparing(SignalByDateEntry::ticker, Comparator.nullsLast(String::compareTo)))
                .toList();
        return Collections.unmodifiableList(orderedSignals);
    }

    public List<SignalHistoryEntry> fetchSignalsHistory(LocalDate from, LocalDate to, int limit) {
        Map<String, QueryParameterValue> params = new LinkedHashMap<>();
        params.put("limit", QueryParameterValue.int64(limit));
        params.put("from", QueryParameterValue.date(from.toString()));
        params.put("to", QueryParameterValue.date(to.toString()));

        String viewSql = "SELECT * FROM " + qualifiedView(properties.getSignalsHistoryView()) + " LIMIT @limit";
        List<SignalHistoryEntry> history;
        try {
            history = querySignalHistory(viewSql, Map.of("limit", params.get("limit")));
        } catch (OpsDataAccessException ex) {
            history = List.of();
        }
        if (history.isEmpty()) {
            history = querySignalHistory(buildSignalsHistoryFallbackSql(), params);
        }

        List<SignalHistoryEntry> filteredHistory = history.stream()
                .filter(entry -> isWithinRange(entry.dateRef(), from, to) || isWithinRange(entry.validFor(), from, to))
                .sorted(Comparator.comparing(
                                SignalHistoryEntry::dateRef,
                                Comparator.nullsLast(Comparator.reverseOrder()))
                        .thenComparing(SignalHistoryEntry::rank, Comparator.nullsLast(Integer::compareTo)))
                .collect(Collectors.toList());
        return Collections.unmodifiableList(filteredHistory);
    }

    private TableResult runQuery(String sql, Map<String, QueryParameterValue> params) {
        QueryJobConfiguration.Builder builder = QueryJobConfiguration.newBuilder(sql).setUseLegacySql(false);
        for (Map.Entry<String, QueryParameterValue> entry : params.entrySet()) {
            builder.addNamedParameter(entry.getKey(), entry.getValue());
        }
        try {
            return bigQuery.query(builder.build());
        } catch (BigQueryException ex) {
            throw new OpsDataAccessException("Falha ao consultar BigQuery", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new OpsDataAccessException("Thread interrompida durante consulta ao BigQuery", ex);
        }
    }

    private OpsOverview toOverview(FieldValueList row) {
        OffsetDateTime asOf = getTimestamp(row, "asOf");
        LocalDate lastTradingDay = getDate(row, "lastTradingDay");
        LocalDate nextTradingDay = getDate(row, "nextTradingDay");
        String pipelineHealth = getString(row, "pipelineHealth");
        String dqHealth = getString(row, "dqHealth");
        Boolean signalsReady = getBoolean(row, "signalsReady");
        Long signalsCount = getLong(row, "signalsCount");
        OffsetDateTime lastSignalsGeneratedAt = getTimestamp(row, "lastSignalsGeneratedAt");
        return new OpsOverview(
                asOf,
                lastTradingDay,
                nextTradingDay,
                pipelineHealth != null ? pipelineHealth : "UNKNOWN",
                dqHealth != null ? dqHealth : "UNKNOWN",
                signalsReady != null && signalsReady,
                signalsCount != null ? signalsCount : 0L,
                lastSignalsGeneratedAt);
    }

    private PipelineJobStatus toPipelineJobStatus(FieldValueList row) {
        return new PipelineJobStatus(
                getString(row, "jobName", "job_name"),
                getTimestamp(row, "lastRunAt", "last_run_at"),
                getString(row, "lastStatus", "last_status"),
                getLong(row, "minutesSinceLastRun", "minutes_since_last_run"),
                getTimestamp(row, "deadlineAt", "deadline_at"),
                Optional.ofNullable(getBoolean(row, "isSilent", "is_silent")).orElse(false),
                getString(row, "lastRunId", "last_run_id"));
    }

    private DqCheck toDqCheck(FieldValueList row) {
        return new DqCheck(
                getDate(row, "checkDate", "check_date"),
                getString(row, "checkName", "check_name"),
                getString(row, "status"),
                getString(row, "details"),
                getTimestamp(row, "createdAt", "created_at"));
    }

    private OpsIncident toIncident(FieldValueList row) {
        return new OpsIncident(
                getString(row, "incidentId", "incident_id"),
                getString(row, "checkName", "check_name"),
                getDate(row, "checkDate", "check_date"),
                getString(row, "severity"),
                getString(row, "source"),
                getString(row, "summary"),
                getString(row, "status"),
                getString(row, "runId", "run_id"),
                getTimestamp(row, "createdAt", "created_at"));
    }

    private NeuralTrainingDataAllocation toNeuralTrainingDataAllocation(FieldValueList row) {
        return new NeuralTrainingDataAllocation(
                getString(row, "feature_version", "featureVersion"),
                getString(row, "label_version", "labelVersion"),
                getString(row, "dataset_split", "datasetSplit"),
                getLong(row, "rows_count", "rowsCount"),
                getLong(row, "tickers_count", "tickersCount"),
                getDate(row, "min_reference_date", "minReferenceDate"),
                getDate(row, "max_reference_date", "maxReferenceDate"),
                getLong(row, "up_count", "upCount"),
                getLong(row, "down_count", "downCount"),
                getLong(row, "neutral_count", "neutralCount"),
                getDouble(row, "up_ratio", "upRatio"),
                getDouble(row, "down_ratio", "downRatio"),
                getDouble(row, "neutral_ratio", "neutralRatio"),
                getLong(row, "missing_ohlcv_count", "missingOhlcvCount"),
                getLong(row, "zero_volume_count", "zeroVolumeCount"),
                getLong(row, "suspicious_candle_count", "suspiciousCandleCount"),
                getLong(row, "target_hit_count", "targetHitCount"),
                getLong(row, "stop_hit_count", "stopHitCount"));
    }

    private NeuralTrainingRun toNeuralTrainingRun(FieldValueList row) {
        return new NeuralTrainingRun(
                getString(row, "model_id", "modelId"),
                getString(row, "model_version", "modelVersion"),
                getString(row, "status"),
                getString(row, "feature_version", "featureVersion"),
                getString(row, "label_version", "labelVersion"),
                getString(row, "training_dataset_snapshot", "trainingDatasetSnapshot"),
                getString(row, "artifact_uri", "artifactUri"),
                getLong(row, "feature_columns_count", "featureColumnsCount"),
                getLong(row, "label_classes_count", "labelClassesCount"),
                getDouble(row, "directional_precision", "directionalPrecision"),
                getDouble(row, "coverage"),
                getDouble(row, "validation_accuracy", "validationAccuracy"),
                getDouble(row, "test_accuracy", "testAccuracy"),
                getString(row, "metrics_json", "metricsJson"),
                getString(row, "confusion_matrix_json", "confusionMatrixJson"),
                getTimestamp(row, "trained_at", "trainedAt"),
                getTimestamp(row, "created_at", "createdAt"),
                getString(row, "notes"));
    }

    private QuantDataInventorySummary toQuantDataInventorySummary(FieldValueList row) {
        return new QuantDataInventorySummary(
                getLong(row, "active_tickers", "activeTickers"),
                getLong(row, "total_tickers", "totalTickers"),
                getLong(row, "daily_tickers", "dailyTickers"),
                getLong(row, "intraday_tickers", "intradayTickers"),
                getDate(row, "first_available_date", "firstAvailableDate"),
                getDate(row, "last_available_date", "lastAvailableDate"),
                getLong(row, "daily_candles", "dailyCandles"),
                getLong(row, "intraday_candles", "intradayCandles"),
                getDouble(row, "valid_data_pct", "validDataPct"),
                getTimestamp(row, "last_update", "lastUpdate"));
    }

    private QuantTickerCoverage toQuantTickerCoverage(FieldValueList row) {
        return new QuantTickerCoverage(
                getString(row, "ticker"),
                getString(row, "empresa", "company"),
                getBoolean(row, "ativo", "active"),
                getDate(row, "first_date", "firstDate"),
                getDate(row, "last_date", "lastDate"),
                getLong(row, "days_with_data", "daysWithData"),
                getLong(row, "expected_days", "expectedDays"),
                getDouble(row, "coverage_pct", "coveragePct"),
                getDouble(row, "avg_financial_volume", "avgFinancialVolume"),
                getLong(row, "invalid_price_days", "invalidPriceDays"),
                getLong(row, "invalid_volume_days", "invalidVolumeDays"),
                getLong(row, "duplicate_days", "duplicateDays"),
                getString(row, "eligibility_status", "eligibilityStatus"));
    }

    private QuantDataQualityIncident toQuantDataQualityIncident(FieldValueList row) {
        return new QuantDataQualityIncident(
                getString(row, "incident_type", "incidentType"),
                getString(row, "severity"),
                getString(row, "ticker"),
                getDate(row, "incident_date", "incidentDate"),
                getString(row, "recommendation"));
    }

    private QuantBaselineStrategy toQuantBaselineStrategy(FieldValueList row) {
        return new QuantBaselineStrategy(
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_family", "strategyFamily"),
                getString(row, "strategy_version", "strategyVersion"),
                getString(row, "hypothesis"),
                getString(row, "configured_status", "configuredStatus"),
                getLong(row, "generated_signals", "generatedSignals"),
                getLong(row, "signal_days", "signalDays"),
                getDate(row, "last_signal_date", "lastSignalDate"),
                getLong(row, "trades"),
                getDouble(row, "expectancy_net_pct", "expectancyNetPct"),
                getDouble(row, "profit_factor", "profitFactor"),
                getDouble(row, "max_drawdown_pct", "maxDrawdownPct"),
                getDouble(row, "robustness_score", "robustnessScore"),
                getString(row, "computed_status", "computedStatus"));
    }

    private QuantStrategyDetailAlert toQuantStrategyDetailAlert(FieldValueList row) {
        String alertsText = getString(row, "alerts_text", "alertsText");
        List<String> alerts = alertsText == null || alertsText.isBlank()
                ? List.of()
                : List.of(alertsText.split("\\|"));
        return new QuantStrategyDetailAlert(
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_version", "strategyVersion"),
                getLong(row, "generated_signals", "generatedSignals"),
                getLong(row, "trades"),
                getDouble(row, "expectancy_net_pct", "expectancyNetPct"),
                getDouble(row, "profit_factor", "profitFactor"),
                getDouble(row, "max_drawdown_pct", "maxDrawdownPct"),
                alerts);
    }

    private QuantRankingDailyEntry toQuantRankingDailyEntry(FieldValueList row) {
        return new QuantRankingDailyEntry(
                getString(row, "ranking_model_id", "rankingModelId"),
                getString(row, "ranking_model_version", "rankingModelVersion"),
                getDate(row, "reference_date", "referenceDate"),
                getLong(row, "ranking_position", "rankingPosition"),
                getLong(row, "ranking_decile", "rankingDecile"),
                getString(row, "ticker"),
                getDouble(row, "final_score", "finalScore"),
                getDouble(row, "relative_strength_factor", "relativeStrengthFactor"),
                getDouble(row, "short_momentum_factor", "shortMomentumFactor"),
                getDouble(row, "relative_volume_factor", "relativeVolumeFactor"),
                getDouble(row, "volatility_factor", "volatilityFactor"),
                getDouble(row, "mean_distance_factor", "meanDistanceFactor"),
                getDouble(row, "candle_quality_factor", "candleQualityFactor"),
                getDouble(row, "index_regime_factor", "indexRegimeFactor"),
                getDouble(row, "current_price", "currentPrice"),
                getDouble(row, "liquidity_value", "liquidityValue"),
                getDouble(row, "estimated_risk", "estimatedRisk"),
                getString(row, "market_regime_label", "marketRegimeLabel"),
                getDouble(row, "forward_return_5d", "forwardReturn5d"),
                getString(row, "factor_breakdown_json", "factorBreakdownJson"),
                getString(row, "action_suggestion", "actionSuggestion"),
                getString(row, "confidence_label", "confidenceLabel"));
    }

    private QuantRankingPerformance toQuantRankingPerformance(FieldValueList row) {
        return new QuantRankingPerformance(
                getString(row, "ranking_model_id", "rankingModelId"),
                getString(row, "ranking_model_version", "rankingModelVersion"),
                getLong(row, "top_n", "topN"),
                getLong(row, "portfolio_days", "portfolioDays"),
                getDouble(row, "avg_top_n_return_5d", "avgTopNReturn5d"),
                getDouble(row, "volatility_top_n_return_5d", "volatilityTopNReturn5d"),
                getDouble(row, "positive_day_rate", "positiveDayRate"),
                getDouble(row, "avg_excess_vs_random_5d", "avgExcessVsRandom5d"),
                getDouble(row, "decile_return_correlation", "decileReturnCorrelation"),
                getDouble(row, "top_decile_return_5d", "topDecileReturn5d"),
                getDouble(row, "bottom_decile_return_5d", "bottomDecileReturn5d"),
                getDouble(row, "top_minus_bottom_decile_return_5d", "topMinusBottomDecileReturn5d"),
                getString(row, "ranking_status", "rankingStatus"));
    }


    private QuantPaperTradingDashboard toQuantPaperTradingDashboard(FieldValueList row) {
        return new QuantPaperTradingDashboard(
                getDate(row, "reference_date", "referenceDate"),
                getLong(row, "open_orders", "openOrders"),
                getLong(row, "closed_orders", "closedOrders"),
                getLong(row, "total_orders", "totalOrders"),
                getDouble(row, "daily_pnl_pct", "dailyPnlPct", "daily_net_pnl_pct", "dailyNetPnlPct"),
                getDouble(row, "cumulative_pnl_pct", "cumulativePnlPct", "accumulated_net_pnl_pct", "accumulatedNetPnlPct"),
                getDouble(row, "avg_slippage_pct", "avgSlippagePct"),
                getDouble(row, "execution_rate", "executionRate"),
                getDouble(row, "avg_abs_divergence_pct", "avgAbsDivergencePct"),
                getString(row, "adherence_status", "adherenceStatus"));
    }

    private QuantPaperTradingOrder toQuantPaperTradingOrder(FieldValueList row) {
        return new QuantPaperTradingOrder(
                getString(row, "paper_order_id", "paperOrderId", "order_id", "orderId"),
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_version", "strategyVersion"),
                getString(row, "ticker"),
                getString(row, "side"),
                getLong(row, "quantity"),
                getDouble(row, "expected_entry_price", "expectedEntryPrice"),
                getDouble(row, "simulated_entry_price", "simulatedEntryPrice"),
                getDouble(row, "expected_exit_price", "expectedExitPrice"),
                getDouble(row, "simulated_exit_price", "simulatedExitPrice"),
                getDouble(row, "net_pnl_pct", "netPnlPct"),
                getDouble(row, "divergence_pct", "divergencePct"),
                getString(row, "order_status", "orderStatus"),
                getString(row, "exit_reason", "exitReason"),
                getTimestamp(row, "opened_at", "openedAt"),
                getTimestamp(row, "closed_at", "closedAt"),
                getString(row, "notes", "observations"));
    }

    private QuantOperationalDiaryEvent toQuantOperationalDiaryEvent(FieldValueList row) {
        return new QuantOperationalDiaryEvent(
                getTimestamp(row, "event_timestamp", "eventTimestamp"),
                getDate(row, "event_date", "eventDate", "reference_date", "referenceDate"),
                getString(row, "event_type", "eventType"),
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_version", "strategyVersion"),
                getString(row, "ticker"),
                getString(row, "side"),
                getString(row, "event_status", "eventStatus", "decision_status", "decisionStatus"),
                getString(row, "event_message", "eventMessage", "reason_code", "reasonCode"),
                getString(row, "operator_notes", "operatorNotes", "user_comment", "userComment"));
    }

    private QuantMarketRegime toQuantMarketRegime(FieldValueList row) {
        return new QuantMarketRegime(
                getDate(row, "reference_date", "referenceDate"),
                getLong(row, "eligible_tickers", "eligibleTickers"),
                getDouble(row, "market_return_5d", "marketReturn5d"),
                getDouble(row, "market_return_20d", "marketReturn20d"),
                getDouble(row, "realized_volatility_20d", "realizedVolatility20d"),
                getDouble(row, "avg_market_volatility_60d", "avgMarketVolatility60d"),
                getDouble(row, "volatility_percentile", "volatilityPercentile"),
                getDouble(row, "pct_above_sma_20", "pctAboveSma20"),
                getDouble(row, "pct_above_sma_50", "pctAboveSma50"),
                getDouble(row, "pct_positive_5d", "pctPositive5d"),
                getDouble(row, "aggregate_financial_volume", "aggregateFinancialVolume"),
                getDouble(row, "aggregate_relative_volume", "aggregateRelativeVolume"),
                getString(row, "market_regime", "marketRegime"),
                getString(row, "regime_indicators_json", "regimeIndicatorsJson"));
    }

    private QuantExposureRecommendation toQuantExposureRecommendation(FieldValueList row) {
        return new QuantExposureRecommendation(
                getString(row, "policy_id", "policyId"),
                getString(row, "policy_version", "policyVersion"),
                getDate(row, "reference_date", "referenceDate"),
                getString(row, "market_regime", "marketRegime"),
                getDouble(row, "market_return_5d", "marketReturn5d"),
                getDouble(row, "market_return_20d", "marketReturn20d"),
                getDouble(row, "realized_volatility_20d", "realizedVolatility20d"),
                getDouble(row, "volatility_percentile", "volatilityPercentile"),
                getDouble(row, "pct_above_sma_20", "pctAboveSma20"),
                getDouble(row, "pct_above_sma_50", "pctAboveSma50"),
                getDouble(row, "aggregate_relative_volume", "aggregateRelativeVolume"),
                getString(row, "exposure_action", "exposureAction"),
                getDouble(row, "max_exposure_pct", "maxExposurePct"),
                getLong(row, "max_trades", "maxTrades"),
                getDouble(row, "risk_per_trade_pct", "riskPerTradePct"),
                getDouble(row, "daily_loss_limit_pct", "dailyLossLimitPct"),
                getString(row, "recommendation_reason", "recommendationReason"));
    }

    private QuantStrategyRegimePerformance toQuantStrategyRegimePerformance(FieldValueList row) {
        return new QuantStrategyRegimePerformance(
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_version", "strategyVersion"),
                getString(row, "market_regime", "marketRegime"),
                getLong(row, "trades"),
                getDouble(row, "expectancy_net_pct", "expectancyNetPct"),
                getDouble(row, "win_rate", "winRate"),
                getDouble(row, "profit_factor", "profitFactor"),
                getDouble(row, "total_net_pnl_pct", "totalNetPnlPct"),
                getString(row, "regime_effect_status", "regimeEffectStatus"));
    }

    private QuantFilterEffectiveness toQuantFilterEffectiveness(FieldValueList row) {
        return new QuantFilterEffectiveness(
                getString(row, "strategy_id", "strategyId"),
                getString(row, "strategy_version", "strategyVersion"),
                getLong(row, "original_trades", "originalTrades"),
                getLong(row, "trades_after_filter", "tradesAfterFilter"),
                getDouble(row, "original_expectancy_net_pct", "originalExpectancyNetPct"),
                getDouble(row, "filtered_expectancy_net_pct", "filteredExpectancyNetPct"),
                getDouble(row, "blocked_expectancy_net_pct", "blockedExpectancyNetPct"),
                getDouble(row, "blocked_trade_pct", "blockedTradePct"),
                getDouble(row, "original_total_net_pnl_pct", "originalTotalNetPnlPct"),
                getDouble(row, "exposure_adjusted_total_net_pnl_pct", "exposureAdjustedTotalNetPnlPct"),
                getString(row, "filter_effectiveness_status", "filterEffectivenessStatus"));
    }

    private Signal toSignal(FieldValueList row) {
        return new Signal(
                getDate(row, "validFor", "valid_for"),
                getString(row, "ticker"),
                getString(row, "side"),
                getDouble(row, "entry"),
                getDouble(row, "target"),
                getDouble(row, "stop"),
                getDouble(row, "score"),
                Optional.ofNullable(getLong(row, "rank")).map(Long::intValue).orElse(null),
                getTimestamp(row, "createdAt", "created_at"));
    }

    private SignalByDateEntry toSignalByDate(FieldValueList row) {
        return new SignalByDateEntry(
                getDate(row, "dateRef", "date_ref"),
                getDate(row, "validFor", "valid_for"),
                getString(row, "ticker"),
                getString(row, "side"),
                getDouble(row, "entry"),
                getDouble(row, "target"),
                getDouble(row, "stop"),
                getDouble(row, "score"),
                Optional.ofNullable(getLong(row, "rank")).map(Long::intValue).orElse(null),
                getTimestamp(row, "createdAt", "created_at"),
                getDate(row, "nextTradingDay", "next_trading_day"),
                getDouble(row, "nextDayHigh", "next_day_high"),
                getDouble(row, "nextDayLow", "next_day_low"));
    }

    private SignalHistoryEntry toSignalHistory(FieldValueList row) {
        return new SignalHistoryEntry(
                getDate(row, "dateRef", "date_ref"),
                getDate(row, "validFor", "valid_for"),
                getString(row, "ticker"),
                getString(row, "side"),
                getDouble(row, "entry"),
                getDouble(row, "target"),
                getDouble(row, "stop"),
                getDouble(row, "score"),
                Optional.ofNullable(getLong(row, "rank")).map(Long::intValue).orElse(null),
                getTimestamp(row, "createdAt", "created_at"));
    }

    private String qualifiedQuantView(String view) {
        String dataset = Optional.ofNullable(properties.getQuantDataset())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_intraday");
        String viewName = Optional.ofNullable(view).filter(value -> !value.isBlank()).orElseThrow();
        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, viewName);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, viewName);
    }

    private String qualifiedView(String view) {
        String dataset = Optional.ofNullable(properties.getDataset()).filter(value -> !value.isBlank()).orElse("monitoring");
        String viewName = Optional.ofNullable(view).filter(value -> !value.isBlank()).orElseThrow();
        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, viewName);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, viewName);
    }

    private String qualifiedSignalsTable() {
        String dataset = Optional.ofNullable(properties.getSignalsTableDataset())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_intraday");
        String tableId = Optional.ofNullable(properties.getSignalsTableId())
                .filter(value -> !value.isBlank())
                .orElse("sinais_eod");
        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, tableId);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, tableId);
    }

    private String qualifiedDailyCandlesTable() {
        String dataset = Optional.ofNullable(properties.getDailyCandlesTableDataset())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_intraday");
        String tableId = Optional.ofNullable(properties.getDailyCandlesTableId())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_ohlcv_diario");
        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, tableId);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, tableId);
    }

    private String qualifiedBacktestTradesTable() {
        String dataset = Optional.ofNullable(properties.getBacktestTradesTableDataset())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_intraday");
        String tableId = Optional.ofNullable(properties.getBacktestTradesTableId())
                .filter(value -> !value.isBlank())
                .orElse("backtest_trades");
        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, tableId);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, tableId);
    }

    private String buildSignalsByDateSql() {
        return "SELECT "
                + "s.date_ref AS dateRef, "
                + "COALESCE(s.valid_for, s.date_ref) AS validFor, "
                + "s.ticker, "
                + "s.side, "
                + "s.entry, "
                + "s.target, "
                + "s.stop, "
                + "s.score, "
                + "CAST(s.rank AS INT64) AS rank, "
                + "s.created_at AS createdAt, "
                + "d.data_pregao AS nextTradingDay, "
                + "d.high AS nextDayHigh, "
                + "d.low AS nextDayLow "
                + "FROM "
                + qualifiedSignalsTable()
                + " s LEFT JOIN "
                + qualifiedDailyCandlesTable()
                + " d ON d.ticker = s.ticker AND d.data_pregao = COALESCE(s.valid_for, s.date_ref) "
                + "WHERE s.date_ref = @date "
                + "ORDER BY rank ASC NULLS LAST, score DESC NULLS LAST, ticker ASC";
    }

    private String buildSignalsNextFallbackSql() {
        String table = qualifiedSignalsTable();
        return "SELECT "
                + "COALESCE(valid_for, date_ref) AS validFor, "
                + "ticker, "
                + "side, "
                + "entry, "
                + "target, "
                + "stop, "
                + "NULL AS score, "
                + "CAST(rank AS INT64) AS rank, "
                + "created_at AS createdAt "
                + "FROM "
                + table
                + " WHERE COALESCE(valid_for, date_ref) = (SELECT MAX(COALESCE(valid_for, date_ref)) FROM "
                + table
                + ") ORDER BY rank ASC NULLS LAST, score DESC NULLS LAST, createdAt DESC LIMIT 5";
    }

    private String buildSignalsHistoryFallbackSql() {
        return "SELECT "
                + "date_ref AS dateRef, "
                + "COALESCE(valid_for, date_ref) AS validFor, "
                + "ticker, "
                + "side, "
                + "entry, "
                + "target, "
                + "stop, "
                + "NULL AS score, "
                + "CAST(rank AS INT64) AS rank, "
                + "created_at AS createdAt "
                + "FROM "
                + qualifiedSignalsTable()
                + " WHERE (date_ref BETWEEN @from AND @to OR COALESCE(valid_for, date_ref) BETWEEN @from AND @to)"
                + " ORDER BY dateRef DESC NULLS LAST, rank ASC NULLS LAST, createdAt DESC LIMIT @limit";
    }

    private String buildBacktestTradesPrimarySql() {
        return "SELECT date_ref AS dateRef, ticker, side, entry, exit_price AS exit, "
                + "exit_reason AS outcome, return_pct AS pnlPct, "
                + "entry_fill_date AS entryDate, entry AS entryPrice, exit_date AS exitDate, "
                + "exit_price AS exitPrice, DATE_DIFF(exit_date, entry_fill_date, DAY) AS daysInTrade, "
                + "NULL AS entryLimitPrice, NULL AS entrySignalScore, "
                + "created_at AS createdAt "
                + "FROM " + qualifiedBacktestTradesTable() + " ORDER BY created_at DESC LIMIT @limit";
    }

    private String buildBacktestTradesFallbackSql() {
        return "SELECT date_ref AS dateRef, ticker, side, entry, exit, outcome, pnl_pct AS pnlPct, "
                + "entry_date AS entryDate, entry AS entryPrice, exit_date AS exitDate, exit AS exitPrice, "
                + "days_in_trade AS daysInTrade, entry_limit_price AS entryLimitPrice, "
                + "signal_score AS entrySignalScore, created_at AS createdAt "
                + "FROM " + qualifiedBacktestTradesTable() + " ORDER BY created_at DESC LIMIT @limit";
    }

    private String buildBacktestTradesLegacyFallbackSql() {
        return "SELECT date_ref AS dateRef, ticker, side, entry_price AS entry, exit_price AS exit, "
                + "outcome, pnl_percent AS pnlPct, "
                + "entry_date AS entryDate, entry_price AS entryPrice, exit_date AS exitDate, "
                + "exit_price AS exitPrice, days AS daysInTrade, limit_price AS entryLimitPrice, "
                + "score AS entrySignalScore, created_at AS createdAt "
                + "FROM " + qualifiedBacktestTradesTable() + " ORDER BY created_at DESC LIMIT @limit";
    }

    private List<Signal> querySignals(String sql, Map<String, QueryParameterValue> params) {
        TableResult result = runQuery(sql, params);
        List<Signal> signals = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            signals.add(toSignal(row));
        }
        return signals;
    }

    private List<SignalHistoryEntry> querySignalHistory(String sql, Map<String, QueryParameterValue> params) {
        TableResult result = runQuery(sql, params);
        List<SignalHistoryEntry> history = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            history.add(toSignalHistory(row));
        }
        return history;
    }

    private String getString(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getStringValue();
        } catch (UnsupportedOperationException ex) {
            Object raw = value.getValue();
            return raw != null ? raw.toString() : null;
        }
    }

    private Boolean getBoolean(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getBooleanValue();
        } catch (UnsupportedOperationException ex) {
            String raw = value.getStringValue();
            if (raw == null) {
                return null;
            }
            return raw.equalsIgnoreCase("true") || raw.equals("1");
        }
    }

    private Long getLong(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getLongValue();
        } catch (UnsupportedOperationException ex) {
            String raw = value.getStringValue();
            if (raw == null || raw.isBlank()) {
                return null;
            }
            try {
                return Long.parseLong(raw.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
    }

    private Double getDouble(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getDoubleValue();
        } catch (UnsupportedOperationException ex) {
            String raw = value.getStringValue();
            if (raw == null || raw.isBlank()) {
                return null;
            }
            try {
                return Double.parseDouble(raw.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
    }

    private LocalDate getDate(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        String raw = value.getStringValue();
        if (raw == null || raw.isBlank()) {
            return null;
        }
        try {
            return LocalDate.parse(raw.trim());
        } catch (DateTimeParseException ex) {
            return null;
        }
    }

    private OffsetDateTime getTimestamp(FieldValueList row, String... fieldNames) {
        FieldValue value = safeGet(row, fieldNames);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getTimestampInstant().atOffset(ZoneOffset.UTC);
        } catch (RuntimeException ex) {
            String raw = value.getStringValue();
            if (raw == null || raw.isBlank()) {
                return null;
            }
            return parseDateTime(raw.trim());
        }
    }

    private OffsetDateTime parseDateTime(String raw) {
        try {
            return OffsetDateTime.parse(raw, DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        } catch (DateTimeParseException ignored) {
            // Try ISO without offset
        }
        try {
            LocalDateTime localDateTime = LocalDateTime.parse(raw.replace(' ', 'T'));
            return localDateTime.atOffset(ZoneOffset.UTC);
        } catch (DateTimeParseException ignored) {
            // Give up
        }
        return null;
    }

    private FieldValue safeGet(FieldValueList row, String... fieldNames) {
        for (String fieldName : fieldNames) {
            if (fieldName == null || fieldName.isBlank()) {
                continue;
            }
            try {
                return row.get(fieldName);
            } catch (IllegalArgumentException ignored) {
                // try next alias
            }
        }
        return null;
    }

    private boolean isWithinRange(LocalDate date, LocalDate from, LocalDate to) {
        return date != null && !date.isBefore(from) && !date.isAfter(to);
    }
}
