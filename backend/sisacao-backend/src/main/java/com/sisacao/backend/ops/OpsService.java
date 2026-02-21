package com.sisacao.backend.ops;

import com.sisacao.backend.ops.bigquery.BigQueryOpsClient;
import com.sisacao.backend.ops.bigquery.OpsBigQueryProperties;
import java.time.LocalDate;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(prefix = "sisacao.ops.bigquery", name = "enabled", havingValue = "true")
public class OpsService {

    private final BigQueryOpsClient bigQueryOpsClient;
    private final OpsBigQueryProperties properties;

    public OpsService(BigQueryOpsClient bigQueryOpsClient, OpsBigQueryProperties properties) {
        this.bigQueryOpsClient = bigQueryOpsClient;
        this.properties = properties;
    }

    public OpsOverview getOverview() {
        return bigQueryOpsClient.fetchOverview();
    }

    public List<PipelineJobStatus> getPipelineStatus() {
        return bigQueryOpsClient.fetchPipelineStatus();
    }

    public List<DqCheck> getLatestDqChecks() {
        return bigQueryOpsClient.fetchLatestDqChecks();
    }

    public List<OpsIncident> getOpenIncidents() {
        return bigQueryOpsClient.fetchOpenIncidents();
    }

    public List<Signal> getNextSignals() {
        return bigQueryOpsClient.fetchNextSignals();
    }

    public List<SignalHistoryEntry> getSignalsHistory(LocalDate from, LocalDate to, Integer limit) {
        validateRange(from, to);
        int sanitizedLimit = sanitizeLimit(limit);
        return bigQueryOpsClient.fetchSignalsHistory(from, to, sanitizedLimit);
    }

    private void validateRange(LocalDate from, LocalDate to) {
        if (from == null || to == null) {
            throw new OpsValidationException("Parâmetros 'from' e 'to' são obrigatórios.");
        }
        if (from.isAfter(to)) {
            throw new OpsValidationException("O parâmetro 'from' não pode ser posterior ao 'to'.");
        }
    }

    private int sanitizeLimit(Integer limit) {
        int maxRows = Math.max(properties.getHistoryMaxRows(), 1);
        if (limit == null) {
            return maxRows;
        }
        if (limit <= 0) {
            throw new OpsValidationException("O parâmetro 'limit' deve ser maior que zero.");
        }
        return Math.min(limit, maxRows);
    }
}
