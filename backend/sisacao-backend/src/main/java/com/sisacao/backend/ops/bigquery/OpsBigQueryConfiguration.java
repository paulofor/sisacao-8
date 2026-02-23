package com.sisacao.backend.ops.bigquery;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryOptions;
import com.sisacao.backend.gcp.GcpCredentialsProvider;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(OpsBigQueryProperties.class)
public class OpsBigQueryConfiguration {

    @Bean
    @ConditionalOnProperty(prefix = "sisacao.ops.bigquery", name = "enabled", havingValue = "true")
    public BigQueryOpsClient bigQueryOpsClient(
            ObjectProvider<BigQuery> bigQueryProvider,
            OpsBigQueryProperties properties,
            GcpCredentialsProvider credentialsProvider) {
        BigQuery bigQuery = bigQueryProvider.getIfAvailable(() -> buildBigQuery(properties, credentialsProvider));
        return new BigQueryOpsClient(bigQuery, properties);
    }

    private BigQuery buildBigQuery(
            OpsBigQueryProperties properties, GcpCredentialsProvider credentialsProvider) {
        BigQueryOptions.Builder builder = BigQueryOptions.newBuilder();
        if (properties.getProjectId() != null && !properties.getProjectId().isBlank()) {
            builder.setProjectId(properties.getProjectId());
        }
        credentialsProvider.getCredentials().ifPresent(builder::setCredentials);
        return builder.build().getService();
    }
}
