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
    private String signalsTableDataset = "cotacao_intraday";
    private String signalsTableId = "sinais_eod";
    private int historyMaxRows = 200;
    private String backtestTradesTableDataset = "cotacao_intraday";
    private String backtestTradesTableId = "backtest_trades";
    private String dailyCandlesTableDataset = "cotacao_intraday";
    private String dailyCandlesTableId = "cotacao_ohlcv_diario";
    private String quantDataset = "cotacao_intraday";
    private String quantInventorySummaryView = "vw_quant_data_inventory_summary";
    private String quantTickerCoverageView = "vw_quant_ticker_coverage";
    private String quantDataQualityIncidentsView = "vw_quant_data_quality_incidents";
    private String quantBaselineStatusView = "vw_quant_phase2_baseline_status";
    private String quantStrategyDetailAlertsView = "vw_quant_phase2_strategy_detail_alerts";
    private String quantRankingDailyView = "vw_quant_phase3_daily_asset_ranking";
    private String quantRankingPerformanceView = "vw_quant_phase3_ranking_performance";
    private String quantMarketRegimeView = "vw_quant_phase4_market_regime_indicators";
    private String quantExposureRecommendationView = "vw_quant_phase4_exposure_recommendation";
    private String quantStrategyRegimePerformanceView = "vw_quant_phase4_strategy_regime_performance";
    private String quantFilterEffectivenessView = "vw_quant_phase4_filter_effectiveness";

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

    public String getSignalsTableDataset() {
        return signalsTableDataset;
    }

    public void setSignalsTableDataset(String signalsTableDataset) {
        if (signalsTableDataset != null && !signalsTableDataset.isBlank()) {
            this.signalsTableDataset = signalsTableDataset;
        }
    }

    public String getSignalsTableId() {
        return signalsTableId;
    }

    public void setSignalsTableId(String signalsTableId) {
        if (signalsTableId != null && !signalsTableId.isBlank()) {
            this.signalsTableId = signalsTableId;
        }
    }


    public String getBacktestTradesTableDataset() {
        return backtestTradesTableDataset;
    }

    public void setBacktestTradesTableDataset(String backtestTradesTableDataset) {
        if (backtestTradesTableDataset != null && !backtestTradesTableDataset.isBlank()) {
            this.backtestTradesTableDataset = backtestTradesTableDataset;
        }
    }

    public String getBacktestTradesTableId() {
        return backtestTradesTableId;
    }

    public void setBacktestTradesTableId(String backtestTradesTableId) {
        if (backtestTradesTableId != null && !backtestTradesTableId.isBlank()) {
            this.backtestTradesTableId = backtestTradesTableId;
        }
    }

    public String getDailyCandlesTableDataset() {
        return dailyCandlesTableDataset;
    }

    public void setDailyCandlesTableDataset(String dailyCandlesTableDataset) {
        if (dailyCandlesTableDataset != null && !dailyCandlesTableDataset.isBlank()) {
            this.dailyCandlesTableDataset = dailyCandlesTableDataset;
        }
    }

    public String getDailyCandlesTableId() {
        return dailyCandlesTableId;
    }

    public void setDailyCandlesTableId(String dailyCandlesTableId) {
        if (dailyCandlesTableId != null && !dailyCandlesTableId.isBlank()) {
            this.dailyCandlesTableId = dailyCandlesTableId;
        }
    }

    public String getQuantDataset() {
        return quantDataset;
    }

    public void setQuantDataset(String quantDataset) {
        if (quantDataset != null && !quantDataset.isBlank()) {
            this.quantDataset = quantDataset;
        }
    }

    public String getQuantInventorySummaryView() {
        return quantInventorySummaryView;
    }

    public void setQuantInventorySummaryView(String quantInventorySummaryView) {
        if (quantInventorySummaryView != null && !quantInventorySummaryView.isBlank()) {
            this.quantInventorySummaryView = quantInventorySummaryView;
        }
    }

    public String getQuantTickerCoverageView() {
        return quantTickerCoverageView;
    }

    public void setQuantTickerCoverageView(String quantTickerCoverageView) {
        if (quantTickerCoverageView != null && !quantTickerCoverageView.isBlank()) {
            this.quantTickerCoverageView = quantTickerCoverageView;
        }
    }

    public String getQuantDataQualityIncidentsView() {
        return quantDataQualityIncidentsView;
    }

    public void setQuantDataQualityIncidentsView(String quantDataQualityIncidentsView) {
        if (quantDataQualityIncidentsView != null && !quantDataQualityIncidentsView.isBlank()) {
            this.quantDataQualityIncidentsView = quantDataQualityIncidentsView;
        }
    }

    public String getQuantBaselineStatusView() {
        return quantBaselineStatusView;
    }

    public void setQuantBaselineStatusView(String quantBaselineStatusView) {
        if (quantBaselineStatusView != null && !quantBaselineStatusView.isBlank()) {
            this.quantBaselineStatusView = quantBaselineStatusView;
        }
    }

    public String getQuantStrategyDetailAlertsView() {
        return quantStrategyDetailAlertsView;
    }

    public void setQuantStrategyDetailAlertsView(String quantStrategyDetailAlertsView) {
        if (quantStrategyDetailAlertsView != null && !quantStrategyDetailAlertsView.isBlank()) {
            this.quantStrategyDetailAlertsView = quantStrategyDetailAlertsView;
        }
    }

    public String getQuantRankingDailyView() {
        return quantRankingDailyView;
    }

    public void setQuantRankingDailyView(String quantRankingDailyView) {
        if (quantRankingDailyView != null && !quantRankingDailyView.isBlank()) {
            this.quantRankingDailyView = quantRankingDailyView;
        }
    }

    public String getQuantRankingPerformanceView() {
        return quantRankingPerformanceView;
    }

    public void setQuantRankingPerformanceView(String quantRankingPerformanceView) {
        if (quantRankingPerformanceView != null && !quantRankingPerformanceView.isBlank()) {
            this.quantRankingPerformanceView = quantRankingPerformanceView;
        }
    }


    public String getQuantMarketRegimeView() {
        return quantMarketRegimeView;
    }

    public void setQuantMarketRegimeView(String quantMarketRegimeView) {
        if (quantMarketRegimeView != null && !quantMarketRegimeView.isBlank()) {
            this.quantMarketRegimeView = quantMarketRegimeView;
        }
    }

    public String getQuantExposureRecommendationView() {
        return quantExposureRecommendationView;
    }

    public void setQuantExposureRecommendationView(String quantExposureRecommendationView) {
        if (quantExposureRecommendationView != null && !quantExposureRecommendationView.isBlank()) {
            this.quantExposureRecommendationView = quantExposureRecommendationView;
        }
    }

    public String getQuantStrategyRegimePerformanceView() {
        return quantStrategyRegimePerformanceView;
    }

    public void setQuantStrategyRegimePerformanceView(String quantStrategyRegimePerformanceView) {
        if (quantStrategyRegimePerformanceView != null && !quantStrategyRegimePerformanceView.isBlank()) {
            this.quantStrategyRegimePerformanceView = quantStrategyRegimePerformanceView;
        }
    }

    public String getQuantFilterEffectivenessView() {
        return quantFilterEffectivenessView;
    }

    public void setQuantFilterEffectivenessView(String quantFilterEffectivenessView) {
        if (quantFilterEffectivenessView != null && !quantFilterEffectivenessView.isBlank()) {
            this.quantFilterEffectivenessView = quantFilterEffectivenessView;
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
