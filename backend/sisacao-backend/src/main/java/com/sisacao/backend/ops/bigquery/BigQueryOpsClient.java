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
import com.sisacao.backend.ops.OpsIncident;
import com.sisacao.backend.ops.OpsOverview;
import com.sisacao.backend.ops.PipelineJobStatus;
import com.sisacao.backend.ops.Signal;
import com.sisacao.backend.ops.SignalHistoryEntry;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

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

    public List<Signal> fetchNextSignals() {
        String sql = "SELECT * FROM " + qualifiedView(properties.getSignalsNextView()) + " ORDER BY rank";
        TableResult result = runQuery(sql, Map.of());
        List<Signal> signals = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            signals.add(toSignal(row));
        }
        return Collections.unmodifiableList(signals);
    }

    public List<SignalHistoryEntry> fetchSignalsHistory(LocalDate from, LocalDate to, int limit) {
        String sql =
                "SELECT * FROM "
                        + qualifiedView(properties.getSignalsHistoryView())
                        + " WHERE validFor BETWEEN @from AND @to"
                        + " ORDER BY validFor DESC, rank ASC"
                        + " LIMIT @limit";
        Map<String, QueryParameterValue> params = new LinkedHashMap<>();
        params.put("from", QueryParameterValue.date(from.toString()));
        params.put("to", QueryParameterValue.date(to.toString()));
        params.put("limit", QueryParameterValue.int64(limit));
        TableResult result = runQuery(sql, params);
        List<SignalHistoryEntry> history = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            history.add(toSignalHistory(row));
        }
        return Collections.unmodifiableList(history);
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
                getString(row, "jobName"),
                getTimestamp(row, "lastRunAt"),
                getString(row, "lastStatus"),
                getLong(row, "minutesSinceLastRun"),
                getTimestamp(row, "deadlineAt"),
                Optional.ofNullable(getBoolean(row, "isSilent")).orElse(false),
                getString(row, "lastRunId"));
    }

    private DqCheck toDqCheck(FieldValueList row) {
        return new DqCheck(
                getDate(row, "checkDate"),
                getString(row, "checkName"),
                getString(row, "status"),
                getString(row, "details"),
                getTimestamp(row, "createdAt"));
    }

    private OpsIncident toIncident(FieldValueList row) {
        return new OpsIncident(
                getString(row, "incidentId"),
                getString(row, "checkName"),
                getDate(row, "checkDate"),
                getString(row, "severity"),
                getString(row, "source"),
                getString(row, "summary"),
                getString(row, "status"),
                getString(row, "runId"),
                getTimestamp(row, "createdAt"));
    }

    private Signal toSignal(FieldValueList row) {
        return new Signal(
                getDate(row, "validFor"),
                getString(row, "ticker"),
                getString(row, "side"),
                getDouble(row, "entry"),
                getDouble(row, "target"),
                getDouble(row, "stop"),
                getDouble(row, "score"),
                Optional.ofNullable(getLong(row, "rank")).map(Long::intValue).orElse(null),
                getTimestamp(row, "createdAt"));
    }

    private SignalHistoryEntry toSignalHistory(FieldValueList row) {
        return new SignalHistoryEntry(
                getDate(row, "dateRef"),
                getDate(row, "validFor"),
                getString(row, "ticker"),
                getString(row, "side"),
                getDouble(row, "entry"),
                getDouble(row, "target"),
                getDouble(row, "stop"),
                getDouble(row, "score"),
                Optional.ofNullable(getLong(row, "rank")).map(Long::intValue).orElse(null),
                getTimestamp(row, "createdAt"));
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

    private String getString(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
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

    private Boolean getBoolean(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
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

    private Long getLong(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
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

    private Double getDouble(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
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

    private LocalDate getDate(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
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

    private OffsetDateTime getTimestamp(FieldValueList row, String fieldName) {
        FieldValue value = safeGet(row, fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getTimestampInstant().atOffset(ZoneOffset.UTC);
        } catch (UnsupportedOperationException ex) {
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

    private FieldValue safeGet(FieldValueList row, String fieldName) {
        try {
            return row.get(fieldName);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }
}
