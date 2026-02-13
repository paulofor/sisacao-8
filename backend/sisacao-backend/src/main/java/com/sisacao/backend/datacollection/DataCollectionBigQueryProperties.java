package com.sisacao.backend.datacollection;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "sisacao.data-collection.bigquery")
public class DataCollectionBigQueryProperties {

    private boolean enabled;
    private String projectId;
    private String dataset = "monitoring";
    private String table = "collection_messages";
    private int maxRows = 200;
    private String intradayDataset = "cotacao_intraday";
    private String intradayTable = "cotacao_b3";
    private int intradayDays = 14;
    private int intradayLatestLimit = 20;

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

    public String getIntradayDataset() {
        return intradayDataset;
    }

    public void setIntradayDataset(String intradayDataset) {
        if (intradayDataset != null && !intradayDataset.isBlank()) {
            this.intradayDataset = intradayDataset;
        }
    }

    public String getIntradayTable() {
        return intradayTable;
    }

    public void setIntradayTable(String intradayTable) {
        if (intradayTable != null && !intradayTable.isBlank()) {
            this.intradayTable = intradayTable;
        }
    }

    public int getIntradayDays() {
        return intradayDays;
    }

    public void setIntradayDays(int intradayDays) {
        if (intradayDays > 0) {
            this.intradayDays = intradayDays;
        }
    }

    public int getIntradayLatestLimit() {
        return intradayLatestLimit;
    }

    public void setIntradayLatestLimit(int intradayLatestLimit) {
        if (intradayLatestLimit > 0) {
            this.intradayLatestLimit = intradayLatestLimit;
        }
    }
}
