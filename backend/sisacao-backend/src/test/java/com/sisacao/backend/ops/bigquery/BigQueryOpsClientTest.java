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
                .contains("FROM `ingestaokraken.cotacao_intraday.sinais_eod` WHERE (date_ref BETWEEN @from AND @to OR valid_for BETWEEN @from AND @to)");
        assertThat(queries.get(1).getNamedParameters().get("from").getValue()).isEqualTo("2026-04-10");
        assertThat(queries.get(1).getNamedParameters().get("to").getValue()).isEqualTo("2026-04-17");
    }
}
