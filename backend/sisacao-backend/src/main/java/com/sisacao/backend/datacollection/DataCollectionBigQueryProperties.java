package com.sisacao.backend.datacollection;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "sisacao.data-collection.bigquery")
public class DataCollectionBigQueryProperties {

    private boolean enabled;
    private String projectId;
    private String dataset = "monitoring";
    private String table = "collection_messages";
    private int maxRows = 200;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getProjectId() {
        return projectId;
    }

    public void setProjectId(String projectId) {
        this.projectId = projectId;
    }

    public String getDataset() {
        return dataset;
    }

    public void setDataset(String dataset) {
        if (dataset != null && !dataset.isBlank()) {
            this.dataset = dataset;
        }
    }

    public String getTable() {
        return table;
    }

    public void setTable(String table) {
        if (table != null && !table.isBlank()) {
            this.table = table;
        }
    }

    public int getMaxRows() {
        return maxRows;
    }

    public void setMaxRows(int maxRows) {
        if (maxRows > 0) {
            this.maxRows = maxRows;
        }
    }
}
