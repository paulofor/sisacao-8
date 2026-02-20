package com.sisacao.backend.ops.bigquery;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "sisacao.ops.bigquery")
public class OpsBigQueryProperties {

    private boolean enabled;
    private String projectId;
    private String dataset = "monitoring";
    private String overviewView = "vw_ops_overview";
    private String pipelineView = "vw_ops_pipeline_status";
    private String dqLatestView = "vw_ops_dq_latest";
    private String incidentsView = "vw_ops_incidents_open";
    private String signalsNextView = "vw_ops_signals_next_session";
    private String signalsHistoryView = "vw_ops_signals_history";
    private int historyMaxRows = 200;

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

    public String getOverviewView() {
        return overviewView;
    }

    public void setOverviewView(String overviewView) {
        if (overviewView != null && !overviewView.isBlank()) {
            this.overviewView = overviewView;
        }
    }

    public String getPipelineView() {
        return pipelineView;
    }

    public void setPipelineView(String pipelineView) {
        if (pipelineView != null && !pipelineView.isBlank()) {
            this.pipelineView = pipelineView;
        }
    }

    public String getDqLatestView() {
        return dqLatestView;
    }

    public void setDqLatestView(String dqLatestView) {
        if (dqLatestView != null && !dqLatestView.isBlank()) {
            this.dqLatestView = dqLatestView;
        }
    }

    public String getIncidentsView() {
        return incidentsView;
    }

    public void setIncidentsView(String incidentsView) {
        if (incidentsView != null && !incidentsView.isBlank()) {
            this.incidentsView = incidentsView;
        }
    }

    public String getSignalsNextView() {
        return signalsNextView;
    }

    public void setSignalsNextView(String signalsNextView) {
        if (signalsNextView != null && !signalsNextView.isBlank()) {
            this.signalsNextView = signalsNextView;
        }
    }

    public String getSignalsHistoryView() {
        return signalsHistoryView;
    }

    public void setSignalsHistoryView(String signalsHistoryView) {
        if (signalsHistoryView != null && !signalsHistoryView.isBlank()) {
            this.signalsHistoryView = signalsHistoryView;
        }
    }

    public int getHistoryMaxRows() {
        return historyMaxRows;
    }

    public void setHistoryMaxRows(int historyMaxRows) {
        if (historyMaxRows > 0) {
            this.historyMaxRows = historyMaxRows;
        }
    }
}
