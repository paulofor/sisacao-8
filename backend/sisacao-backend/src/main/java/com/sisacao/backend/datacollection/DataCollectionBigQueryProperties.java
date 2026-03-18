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
    private String dailyDataset = "cotacao_intraday";
    private String dailyTable = "cotacao_ohlcv_diario";
    private int dailyDays = 5;
    private String candlesDataset = "cotacao_intraday";
    private String candlesDailyTable = "candles_diarios";
    private String candlesIntraday15mTable = "candles_intraday_15m";
    private String candlesIntraday1hTable = "candles_intraday_1h";

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

    public String getDailyDataset() {
        return dailyDataset;
    }

    public void setDailyDataset(String dailyDataset) {
        if (dailyDataset != null && !dailyDataset.isBlank()) {
            this.dailyDataset = dailyDataset;
        }
    }

    public String getDailyTable() {
        return dailyTable;
    }

    public void setDailyTable(String dailyTable) {
        if (dailyTable != null && !dailyTable.isBlank()) {
            this.dailyTable = dailyTable;
        }
    }

    public int getDailyDays() {
        return dailyDays;
    }

    public void setDailyDays(int dailyDays) {
        if (dailyDays > 0) {
            this.dailyDays = dailyDays;
        }
    }

    public String getCandlesDataset() {
        return candlesDataset;
    }

    public void setCandlesDataset(String candlesDataset) {
        if (candlesDataset != null && !candlesDataset.isBlank()) {
            this.candlesDataset = candlesDataset;
        }
    }

    public String getCandlesDailyTable() {
        return candlesDailyTable;
    }

    public void setCandlesDailyTable(String candlesDailyTable) {
        if (candlesDailyTable != null && !candlesDailyTable.isBlank()) {
            this.candlesDailyTable = candlesDailyTable;
        }
    }

    public String getCandlesIntraday15mTable() {
        return candlesIntraday15mTable;
    }

    public void setCandlesIntraday15mTable(String candlesIntraday15mTable) {
        if (candlesIntraday15mTable != null && !candlesIntraday15mTable.isBlank()) {
            this.candlesIntraday15mTable = candlesIntraday15mTable;
        }
    }

    public String getCandlesIntraday1hTable() {
        return candlesIntraday1hTable;
    }

    public void setCandlesIntraday1hTable(String candlesIntraday1hTable) {
        if (candlesIntraday1hTable != null && !candlesIntraday1hTable.isBlank()) {
            this.candlesIntraday1hTable = candlesIntraday1hTable;
        }
    }

}
