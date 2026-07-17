package com.sisacao.backend.ops.bigquery;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.QueryParameterValue;
import com.google.cloud.bigquery.TableResult;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class BigQueryOpsClientTest {

    @Test
    void shouldQuerySignalsByDateJoiningDailyCandles() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult tableResult = mock(TableResult.class);
        doReturn(List.of()).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setSignalsTableDataset("cotacao_intraday");
        properties.setSignalsTableId("sinais_eod");
        properties.setDailyCandlesTableDataset("cotacao_intraday");
        properties.setDailyCandlesTableId("cotacao_ohlcv_diario");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);

        client.fetchSignalsByDate(LocalDate.parse("2026-04-10"));

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());
        QueryJobConfiguration queryConfig = queryCaptor.getValue();

        assertThat(queryConfig.getQuery())
                .contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod` s LEFT JOIN `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario` d")
                .contains("d.data_pregao = COALESCE(s.valid_for, s.date_ref)")
                .contains("WHERE s.date_ref = @date");
        assertThat(queryConfig.getNamedParameters().get("date").getValue()).isEqualTo("2026-04-10");
    }


    @Test
    void shouldQueryNeuralTrainingRunsWithRegistryTotals() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult tableResult = mock(TableResult.class);
        doReturn(List.of()).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setQuantDataset("cotacao_intraday");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchNeuralTrainingRuns();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());
        QueryJobConfiguration queryConfig = queryCaptor.getValue();

        assertThat(queryConfig.getQuery())
                .contains("FROM `ingestaokraken.cotacao_intraday.neural_model_registry` r")
                .contains("WHERE LOWER(gd.candidate_family_hash) = LOWER(r.model_version)")
                .contains("LOWER(JSON_VALUE(r.metrics_json, '$.muen_economics.candidate_family_hash'))")
                .contains("COUNT(*) OVER () AS total_runs")
                .contains("COUNTIF(LOWER(status) = 'candidate') OVER () AS candidate_runs")
                .contains("COUNTIF(LOWER(status) = 'approved') OVER () AS approved_runs")
                .contains("COUNTIF(LOWER(status) IN ('rejected', 'reject')) OVER () AS rejected_runs")
                .contains("COUNTIF(LOWER(status) IN ('running', 'training', 'in_progress')) OVER () AS active_training_runs")
                .contains("AS phase3_runs")
                .contains("AS pending_gate_candidate_runs")
                .contains("FROM `ingestaokraken.cotacao_intraday.neural_gate_decisions` gd")
                .contains("ORDER BY trained_at DESC, created_at DESC LIMIT 1000");
    }

    @Test
    void shouldQueryEvolutionActivityWithQualityTestAndGateApprovalTotals() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult tableResult = mock(TableResult.class);
        doReturn(List.of()).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setQuantDataset("cotacao_intraday");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchNeuralEvolutionActivity();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());

        assertThat(queryCaptor.getValue().getQuery())
                .contains("WITH gate_decisions_by_run AS")
                .contains("FROM `ingestaokraken.cotacao_intraday.neural_candidate_configs` config")
                .contains("LOWER(decision.candidate_family_hash) = LOWER(config.dedupe_hash)")
                .contains("AS gate_decisions_count")
                .contains("AS approved_gate_decisions_count")
                .contains("LEFT JOIN gate_decisions_by_run gate USING (evolution_run_id)");
    }

    @Test
    void shouldQueryNeuralGateDecisionsWithFamilyMetrics() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult tableResult = mock(TableResult.class);
        doReturn(List.of()).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setQuantDataset("cotacao_intraday");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchNeuralGateDecisions();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());
        QueryJobConfiguration queryConfig = queryCaptor.getValue();

        assertThat(queryConfig.getQuery())
                .contains("FROM `ingestaokraken.cotacao_intraday.neural_gate_decisions` d")
                .contains("LEFT JOIN (SELECT * FROM `ingestaokraken.cotacao_intraday.neural_family_evaluations`")
                .contains("ROW_NUMBER() OVER (PARTITION BY protocol_version, dataset_snapshot, candidate_family_hash ORDER BY created_at DESC) = 1")
                .contains("COUNT(*) OVER () AS total_decisions")
                .contains("COUNTIF(d.decision_status = 'rejected' OR d.passed = FALSE) OVER () AS rejected_decisions")
                .contains("COUNTIF(d.decision_status = 'passed' OR d.passed = TRUE) OVER () AS passed_decisions")
                .contains("ARRAY_TO_STRING(d.failed_criteria, ', ') AS failed_criteria")
                .contains("ORDER BY d.decided_at DESC LIMIT 1000");
    }

    @Test
    void shouldQuerySignalsHistoryWithLimitParameter() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult tableResult = mock(TableResult.class);
        doReturn(List.of()).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setDataset("monitoring");
        properties.setSignalsHistoryView("vw_ops_signals_history");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);

        client.fetchSignalsHistory(LocalDate.parse("2026-04-10"), LocalDate.parse("2026-04-17"), 100);

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());
        QueryJobConfiguration queryConfig = queryCaptor.getAllValues().get(0);

        assertThat(queryConfig.getQuery()).contains("SELECT * FROM `ingestaokraken.monitoring.vw_ops_signals_history` LIMIT @limit");

        QueryParameterValue limitParam = queryConfig.getNamedParameters().get("limit");

        assertThat(limitParam.getValue()).isEqualTo("100");
    }

    @Test
    void shouldFallbackToSignalsTableWhenSignalsNextViewIsEmpty() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult emptyViewResult = mock(TableResult.class);
        TableResult emptyFallbackResult = mock(TableResult.class);
        doReturn(List.of()).when(emptyViewResult).iterateAll();
        doReturn(List.of()).when(emptyFallbackResult).iterateAll();
        doReturn(emptyViewResult, emptyFallbackResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setDataset("monitoring");
        properties.setSignalsNextView("vw_ops_signals_next_session");
        properties.setSignalsTableDataset("cotacao_intraday");
        properties.setSignalsTableId("sinais_eod");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchNextSignals();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());

        List<QueryJobConfiguration> queries = queryCaptor.getAllValues();
        assertThat(queries.get(0).getQuery()).contains("SELECT * FROM `ingestaokraken.monitoring.vw_ops_signals_next_session`");
        assertThat(queries.get(1).getQuery()).contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod`");
        assertThat(queries.get(1).getQuery()).contains("LIMIT 5");
    }

    @Test
    void shouldFallbackToSignalsTableWhenSignalsHistoryViewIsEmpty() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult emptyViewResult = mock(TableResult.class);
        TableResult emptyFallbackResult = mock(TableResult.class);
        doReturn(List.of()).when(emptyViewResult).iterateAll();
        doReturn(List.of()).when(emptyFallbackResult).iterateAll();
        doReturn(emptyViewResult, emptyFallbackResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setDataset("monitoring");
        properties.setSignalsHistoryView("vw_ops_signals_history");
        properties.setSignalsTableDataset("cotacao_intraday");
        properties.setSignalsTableId("sinais_eod");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchSignalsHistory(LocalDate.parse("2026-04-10"), LocalDate.parse("2026-04-17"), 100);

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());

        List<QueryJobConfiguration> queries = queryCaptor.getAllValues();
        assertThat(queries.get(0).getQuery()).contains("SELECT * FROM `ingestaokraken.monitoring.vw_ops_signals_history` LIMIT @limit");
        assertThat(queries.get(1).getQuery())
                .contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod` WHERE (date_ref BETWEEN @from AND @to OR COALESCE(valid_for, date_ref) BETWEEN @from AND @to)");
        assertThat(queries.get(1).getNamedParameters().get("from").getValue()).isEqualTo("2026-04-10");
        assertThat(queries.get(1).getNamedParameters().get("to").getValue()).isEqualTo("2026-04-17");
    }

    @Test
    void shouldFallbackWhenSignalsNextViewQueryFails() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult fallbackResult = mock(TableResult.class);
        doReturn(List.of()).when(fallbackResult).iterateAll();
        org.mockito.Mockito.doThrow(new com.google.cloud.bigquery.BigQueryException(404, "dataset not found"))
                .doReturn(fallbackResult)
                .when(bigQuery)
                .query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setDataset("monitoring");
        properties.setSignalsNextView("vw_ops_signals_next_session");
        properties.setSignalsTableDataset("cotacao_intraday");
        properties.setSignalsTableId("sinais_eod");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchNextSignals();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());
        List<QueryJobConfiguration> queries = queryCaptor.getAllValues();
        assertThat(queries.get(0).getQuery()).contains("vw_ops_signals_next_session");
        assertThat(queries.get(1).getQuery()).contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod`");
    }

    @Test
    void shouldFallbackWhenSignalsHistoryViewQueryFails() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult fallbackResult = mock(TableResult.class);
        doReturn(List.of()).when(fallbackResult).iterateAll();
        org.mockito.Mockito.doThrow(new com.google.cloud.bigquery.BigQueryException(404, "dataset not found"))
                .doReturn(fallbackResult)
                .when(bigQuery)
                .query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setDataset("monitoring");
        properties.setSignalsHistoryView("vw_ops_signals_history");
        properties.setSignalsTableDataset("cotacao_intraday");
        properties.setSignalsTableId("sinais_eod");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchSignalsHistory(LocalDate.parse("2026-04-10"), LocalDate.parse("2026-04-17"), 100);

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());
        List<QueryJobConfiguration> queries = queryCaptor.getAllValues();
        assertThat(queries.get(0).getQuery()).contains("vw_ops_signals_history");
        assertThat(queries.get(1).getQuery()).contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod`");
    }

    @Test
    void shouldFallbackWhenBacktestPrimaryQueryFails() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        TableResult fallbackResult = mock(TableResult.class);
        doReturn(List.of()).when(fallbackResult).iterateAll();
        org.mockito.Mockito.doThrow(new com.google.cloud.bigquery.BigQueryException(400, "column entry not found"))
                .doReturn(fallbackResult)
                .when(bigQuery)
                .query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setBacktestTradesTableDataset("cotacao_intraday");
        properties.setBacktestTradesTableId("backtest_trades");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);
        client.fetchLatestBacktestTrades(50);

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery, times(2)).query(queryCaptor.capture());
        List<QueryJobConfiguration> queries = queryCaptor.getAllValues();
        assertThat(queries.get(0).getQuery()).contains("entry, exit_price AS exit, exit_reason AS outcome, return_pct AS pnlPct");
        assertThat(queries.get(1).getQuery()).contains("entry, exit, outcome, pnl_pct AS pnlPct");
    }

    @Test
    void shouldReturnEmptyNeuralEvolutionLeaderboardWhenViewIsMissing() throws Exception {
        BigQuery bigQuery = mock(BigQuery.class);
        org.mockito.Mockito.doThrow(new com.google.cloud.bigquery.BigQueryException(404, "Not found: Table ingestaokraken:cotacao_intraday.vw_neural_evolution_leaderboard"))
                .when(bigQuery)
                .query(any(QueryJobConfiguration.class));

        OpsBigQueryProperties properties = new OpsBigQueryProperties();
        properties.setProjectId("ingestaokraken");
        properties.setQuantDataset("cotacao_intraday");
        properties.setNeuralEvolutionLeaderboardView("vw_neural_evolution_leaderboard");

        BigQueryOpsClient client = new BigQueryOpsClient(bigQuery, properties);

        assertThat(client.fetchNeuralEvolutionLeaderboard()).isEmpty();

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());
        assertThat(queryCaptor.getValue().getQuery()).contains("vw_neural_evolution_leaderboard");
    }

}
