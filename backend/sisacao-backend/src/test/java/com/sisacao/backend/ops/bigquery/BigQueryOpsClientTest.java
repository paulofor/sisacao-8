package com.sisacao.backend.ops.bigquery;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
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
    void shouldFilterSignalsHistoryByDateRefOrValidFor() throws Exception {
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
        verify(bigQuery).query(queryCaptor.capture());
        QueryJobConfiguration queryConfig = queryCaptor.getValue();

        assertThat(queryConfig.getQuery())
                .contains("(dateRef BETWEEN @from AND @to OR validFor BETWEEN @from AND @to)")
                .contains("ORDER BY dateRef DESC, rank ASC");

        QueryParameterValue fromParam = queryConfig.getNamedParameters().get("from");
        QueryParameterValue toParam = queryConfig.getNamedParameters().get("to");
        QueryParameterValue limitParam = queryConfig.getNamedParameters().get("limit");

        assertThat(fromParam.getValue()).isEqualTo("2026-04-10");
        assertThat(toParam.getValue()).isEqualTo("2026-04-17");
        assertThat(limitParam.getValue()).isEqualTo("100");
    }
}
