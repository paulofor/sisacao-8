import RefreshIcon from '@mui/icons-material/Refresh'
import AssessmentIcon from '@mui/icons-material/Assessment'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import BarChartIcon from '@mui/icons-material/BarChart'
import ChecklistIcon from '@mui/icons-material/Checklist'
import DashboardIcon from '@mui/icons-material/Dashboard'
import InsightsIcon from '@mui/icons-material/Insights'
import InventoryIcon from '@mui/icons-material/Inventory'
import ScienceIcon from '@mui/icons-material/Science'
import ModelTrainingIcon from '@mui/icons-material/ModelTraining'
import TimelineIcon from '@mui/icons-material/Timeline'
import {
  AppBar,
  Box,
  Button,
  Container,
  Divider,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Toolbar,
  Typography,
} from '@mui/material'
import type { UseQueryResult } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'

import type { DataCollectionMessage, DataCollectionMessageSeverity } from './api/dataCollections'
import BacktestTab from './components/tabs/BacktestTab'
import AiAdvisorTab from './components/tabs/AiAdvisorTab'
import ColetasTab from './components/tabs/ColetasTab'
import IncidentesTab from './components/tabs/IncidentesTab'
import OperacaoTab from './components/tabs/OperacaoTab'
import QuantPhase0Tab from './components/tabs/QuantPhase0Tab'
import NeuralTrainingDataTab from './components/tabs/NeuralTrainingDataTab'
import NeuralEvolutionTab from './components/tabs/NeuralEvolutionTab'
import NeuralTrainingRunsTab from './components/tabs/NeuralTrainingRunsTab'
import QuantRoadmapTab, { type QuantRoadmapKey } from './components/tabs/QuantRoadmapTab'
import SinaisTab from './components/tabs/SinaisTab'
import { useCandlesTableDailyCounts } from './hooks/useCandlesTableDailyCounts'
import { useDataCollectionMessages } from './hooks/useDataCollectionMessages'
import { useDailyTableCounts } from './hooks/useDailyTableCounts'
import { useIntradayDailyCounts } from './hooks/useIntradayDailyCounts'
import { useIntradayLatestRecords } from './hooks/useIntradayLatestRecords'
import { useIntradaySummary } from './hooks/useIntradaySummary'
import { useOpsBacktestTrades } from './hooks/useOpsBacktestTrades'
import { useOpsDqLatest } from './hooks/useOpsDqLatest'
import { useOpsIncidentsOpen } from './hooks/useOpsIncidentsOpen'
import { useOpsOverview } from './hooks/useOpsOverview'
import { useOpsPipeline } from './hooks/useOpsPipeline'
import { useNeuralTrainingDataAllocation } from './hooks/useNeuralTrainingDataAllocation'
import { useNeuralEvolutionLeaderboard } from './hooks/useNeuralEvolutionLeaderboard'
import { useNeuralTrainingRuns } from './hooks/useNeuralTrainingRuns'
import { useOpsSignalsNext } from './hooks/useOpsSignalsNext'
import { useQuantDataInventorySummary } from './hooks/useQuantDataInventorySummary'
import { useQuantBaselineStrategies } from './hooks/useQuantBaselineStrategies'
import { useQuantDataQualityIncidents } from './hooks/useQuantDataQualityIncidents'
import { useQuantStrategyDetailAlerts } from './hooks/useQuantStrategyDetailAlerts'
import { useQuantRankingDaily } from './hooks/useQuantRankingDaily'
import { useQuantRankingPerformance } from './hooks/useQuantRankingPerformance'
import { useQuantMarketRegime } from './hooks/useQuantMarketRegime'
import { useQuantExposureRecommendations } from './hooks/useQuantExposureRecommendations'
import { useQuantStrategyRegimePerformance } from './hooks/useQuantStrategyRegimePerformance'
import { useQuantFilterEffectiveness } from './hooks/useQuantFilterEffectiveness'
import { useQuantPaperTrading } from './hooks/useQuantPaperTrading'
import { useQuantRobustness } from './hooks/useQuantRobustness'
import { useQuantCommittee } from './hooks/useQuantCommittee'
import { useQuantTickerCoverage } from './hooks/useQuantTickerCoverage'

const severityOptions: Array<'all' | DataCollectionMessageSeverity> = [
  'all',
  'SUCCESS',
  'INFO',
  'WARNING',
  'ERROR',
  'CRITICAL',
]

const filterMessagesBySearch = (messages: DataCollectionMessage[], searchTerm: string) => {
  const normalized = searchTerm.trim().toLowerCase()
  if (!normalized) {
    return messages
  }
  return messages.filter((message) => {
    return [message.collector, message.dataset, message.summary]
      .filter(Boolean)
      .some((field) => field.toLowerCase().includes(normalized))
  })
}

type TabValue =
  | 'coletas'
  | 'operacao'
  | 'quant-fase0'
  | 'sinais'
  | 'incidentes'
  | 'backtest'
  | 'quant-roadmap'
  | 'neural-training-data'
  | 'neural-training-runs'
  | 'neural-evolution'
  | 'ai-advisor'

type MenuItem = {
  label: string
  value: TabValue
  icon: typeof DashboardIcon
  roadmapKey?: QuantRoadmapKey
}

const menuGroups: Array<{ title: string; items: MenuItem[] }> = [
  {
    title: 'Operação',
    items: [
      { label: 'Coletas', value: 'coletas', icon: InventoryIcon },
      { label: 'Pipeline', value: 'operacao', icon: DashboardIcon },
      { label: 'Sinais EOD', value: 'sinais', icon: InsightsIcon },
      { label: 'Incidentes', value: 'incidentes', icon: ChecklistIcon },
    ],
  },
  {
    title: 'Redes neurais',
    items: [
      { label: 'Dados de treino', value: 'neural-training-data', icon: ScienceIcon },
      { label: 'Treinos', value: 'neural-training-runs', icon: ModelTrainingIcon },
      { label: 'Evolução', value: 'neural-evolution', icon: TimelineIcon },
      { label: 'Advisor IA Gemini', value: 'ai-advisor', icon: AutoAwesomeIcon },
    ],
  },
  {
    title: 'Sistemas quantitativos',
    items: [
      { label: 'Fase 0 · Inventário', value: 'quant-fase0', icon: AssessmentIcon },
      { label: 'Fase 1 · Backtest', value: 'backtest', icon: BarChartIcon },
      { label: 'Fase 2 · Baselines', value: 'quant-roadmap', icon: ScienceIcon, roadmapKey: 'baseline' },
      { label: 'Fase 3 · Ranking', value: 'quant-roadmap', icon: TimelineIcon, roadmapKey: 'ranking' },
      { label: 'Fase 4 · Regime/Exposição', value: 'quant-roadmap', icon: DashboardIcon, roadmapKey: 'regime' },
      { label: 'Fase 5 · Robustez', value: 'quant-roadmap', icon: AssessmentIcon, roadmapKey: 'robustez' },
      { label: 'Fase 6 · Paper Trading', value: 'quant-roadmap', icon: InsightsIcon, roadmapKey: 'paper' },
      { label: 'Fase 7 · Comitê/Risco', value: 'quant-roadmap', icon: ChecklistIcon, roadmapKey: 'comite' },
    ],
  },
]

type QueryResult = UseQueryResult<unknown, Error>

function App() {
  const [activeTab, setActiveTab] = useState<TabValue>('coletas')
  const [selectedRoadmapKey, setSelectedRoadmapKey] = useState<QuantRoadmapKey>('baseline')
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | DataCollectionMessageSeverity>('all')
  const [searchTerm, setSearchTerm] = useState('')

  const dataCollectionMessagesQuery = useDataCollectionMessages({
    severity: selectedSeverity === 'all' ? undefined : selectedSeverity,
  })
  const intradaySummaryQuery = useIntradaySummary()
  const intradayDailyCountsQuery = useIntradayDailyCounts()
  const intradayLatestRecordsQuery = useIntradayLatestRecords()
  const dailyTableCountsQuery = useDailyTableCounts()
  const candlesTableDailyCountsQuery = useCandlesTableDailyCounts()

  const opsOverviewQuery = useOpsOverview()
  const opsPipelineQuery = useOpsPipeline()
  const opsDqLatestQuery = useOpsDqLatest()
  const opsSignalsNextQuery = useOpsSignalsNext()
  const opsIncidentsOpenQuery = useOpsIncidentsOpen()
  const opsBacktestTradesQuery = useOpsBacktestTrades(200)
  const quantInventorySummaryQuery = useQuantDataInventorySummary()
  const neuralTrainingDataAllocationQuery = useNeuralTrainingDataAllocation()
  const neuralTrainingRunsQuery = useNeuralTrainingRuns()
  const neuralEvolutionLeaderboardQuery = useNeuralEvolutionLeaderboard()
  const quantTickerCoverageQuery = useQuantTickerCoverage(150)
  const quantDataQualityIncidentsQuery = useQuantDataQualityIncidents(150)
  const quantBaselineStrategiesQuery = useQuantBaselineStrategies()
  const quantStrategyDetailAlertsQuery = useQuantStrategyDetailAlerts()
  const quantRankingDailyQuery = useQuantRankingDaily(150)
  const quantRankingPerformanceQuery = useQuantRankingPerformance()
  const quantMarketRegimeQuery = useQuantMarketRegime(90)
  const quantExposureRecommendationsQuery = useQuantExposureRecommendations(90)
  const quantStrategyRegimePerformanceQuery = useQuantStrategyRegimePerformance()
  const quantFilterEffectivenessQuery = useQuantFilterEffectiveness()
  const quantRobustnessQuery = useQuantRobustness()
  const quantPaperTradingQuery = useQuantPaperTrading(150)
  const quantCommitteeQuery = useQuantCommittee(150)

  const messages = useMemo(() => dataCollectionMessagesQuery.data ?? [], [dataCollectionMessagesQuery.data])

  const filteredMessages = useMemo(
    () => filterMessagesBySearch(messages, searchTerm),
    [messages, searchTerm],
  )

  const tabQueries: Record<TabValue, QueryResult[]> = {
    coletas: [
      dataCollectionMessagesQuery,
      intradaySummaryQuery,
      intradayDailyCountsQuery,
      dailyTableCountsQuery,
      intradayLatestRecordsQuery,
      candlesTableDailyCountsQuery,
    ] as QueryResult[],
    operacao: [opsOverviewQuery, opsPipelineQuery, opsDqLatestQuery] as QueryResult[],
    'quant-fase0': [quantInventorySummaryQuery, quantTickerCoverageQuery, quantDataQualityIncidentsQuery] as QueryResult[],
    'neural-training-data': [neuralTrainingDataAllocationQuery] as QueryResult[],
    'neural-training-runs': [neuralTrainingRunsQuery] as QueryResult[],
    'neural-evolution': [neuralEvolutionLeaderboardQuery] as QueryResult[],
    'ai-advisor': [neuralEvolutionLeaderboardQuery] as QueryResult[],
    sinais: [opsSignalsNextQuery] as QueryResult[],
    incidentes: [opsIncidentsOpenQuery] as QueryResult[],
    backtest: [opsBacktestTradesQuery] as QueryResult[],
    'quant-roadmap': selectedRoadmapKey === 'baseline'
      ? [quantBaselineStrategiesQuery, quantStrategyDetailAlertsQuery] as QueryResult[]
      : selectedRoadmapKey === 'ranking'
        ? [quantRankingDailyQuery, quantRankingPerformanceQuery] as QueryResult[]
        : selectedRoadmapKey === 'regime'
          ? [
              quantMarketRegimeQuery,
              quantExposureRecommendationsQuery,
              quantStrategyRegimePerformanceQuery,
              quantFilterEffectivenessQuery,
            ] as QueryResult[]
          : selectedRoadmapKey === 'robustez'
            ? [quantRobustnessQuery] as QueryResult[]
            : selectedRoadmapKey === 'paper'
              ? [quantPaperTradingQuery] as QueryResult[]
              : selectedRoadmapKey === 'comite'
                ? [quantCommitteeQuery] as QueryResult[]
                : [] as QueryResult[],
  }

  const activeQueries = tabQueries[activeTab]
  const isTabLoading = activeQueries.some((query) => query.isLoading)
  const isRefreshing = activeQueries.some((query) => query.isFetching)
  const lastUpdatedAt = activeQueries.reduce<number>((latest, query) => {
    const updatedAt = query.dataUpdatedAt ?? 0
    return updatedAt > latest ? updatedAt : latest
  }, 0)

  const lastUpdatedLabel = lastUpdatedAt
    ? `Atualizado às ${dayjs(lastUpdatedAt).format('HH:mm:ss')}`
    : 'Aguardando atualização'

  const handleRefresh = () => {
    void Promise.all(activeQueries.map((query) => query.refetch()))
  }

  const handleMenuClick = (item: MenuItem) => {
    if (item.roadmapKey) {
      setSelectedRoadmapKey(item.roadmapKey)
    }
    setActiveTab(item.value)
  }

  const intradaySummaryLoading = intradaySummaryQuery.isLoading && !intradaySummaryQuery.data
  const intradayDailyCountsLoading = intradayDailyCountsQuery.isLoading && !intradayDailyCountsQuery.data
  const intradayLatestRecordsLoading = intradayLatestRecordsQuery.isLoading && !intradayLatestRecordsQuery.data
  const dailyTableCountsLoading = dailyTableCountsQuery.isLoading && !dailyTableCountsQuery.data
  const candlesTableDailyCountsLoading =
    candlesTableDailyCountsQuery.isLoading && !candlesTableDailyCountsQuery.data

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" color="transparent" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Typography variant="h6" color="text.primary" sx={{ flexGrow: 1 }}>
            Painel Operacional — Sisacao-8
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {lastUpdatedLabel}
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            Atualizar
          </Button>
        </Toolbar>
        {isTabLoading || isRefreshing ? <LinearProgress color="primary" /> : null}
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '280px minmax(0, 1fr)' }, gap: 3 }}>
          <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2, alignSelf: 'start' }}>
            <Typography variant="overline" color="text.secondary">Menu</Typography>
            {menuGroups.map((group) => (
              <Box key={group.title} sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ px: 1, mb: 0.5 }}>
                  {group.title}
                </Typography>
                <List dense disablePadding>
                  {group.items.map((item) => {
                    const Icon = item.icon
                    const selected = activeTab === item.value && (!item.roadmapKey || selectedRoadmapKey === item.roadmapKey)
                    return (
                      <ListItemButton
                        key={`${group.title}-${item.label}`}
                        selected={selected}
                        onClick={() => handleMenuClick(item)}
                        sx={{ borderRadius: 1 }}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}><Icon fontSize="small" /></ListItemIcon>
                        <ListItemText primary={item.label} />
                      </ListItemButton>
                    )
                  })}
                </List>
                <Divider sx={{ mt: 1 }} />
              </Box>
            ))}
          </Paper>
          <Box>
        {activeTab === 'coletas' ? (
          <ColetasTab
            severityOptions={severityOptions}
            selectedSeverity={selectedSeverity}
            onSeverityChange={setSelectedSeverity}
            searchTerm={searchTerm}
            onSearchTermChange={setSearchTerm}
            messages={filteredMessages}
            messagesError={dataCollectionMessagesQuery.error}
            intradaySummary={intradaySummaryQuery.data}
            intradaySummaryError={intradaySummaryQuery.error}
            intradaySummaryLoading={intradaySummaryLoading}
            intradayDailyCounts={intradayDailyCountsQuery.data}
            intradayDailyCountsError={intradayDailyCountsQuery.error}
            intradayDailyCountsLoading={intradayDailyCountsLoading}
            intradayLatestRecords={intradayLatestRecordsQuery.data}
            intradayLatestRecordsError={intradayLatestRecordsQuery.error}
            intradayLatestRecordsLoading={intradayLatestRecordsLoading}
            dailyTableCounts={dailyTableCountsQuery.data}
            dailyTableCountsError={dailyTableCountsQuery.error}
            dailyTableCountsLoading={dailyTableCountsLoading}
            candlesTableDailyCounts={candlesTableDailyCountsQuery.data}
            candlesTableDailyCountsError={candlesTableDailyCountsQuery.error}
            candlesTableDailyCountsLoading={candlesTableDailyCountsLoading}
          />
        ) : null}

        {activeTab === 'operacao' ? (
          <OperacaoTab
            overview={opsOverviewQuery.data}
            overviewError={opsOverviewQuery.error}
            overviewLoading={opsOverviewQuery.isLoading && !opsOverviewQuery.data}
            pipelineJobs={opsPipelineQuery.data ?? []}
            pipelineError={opsPipelineQuery.error}
            pipelineLoading={opsPipelineQuery.isLoading && (opsPipelineQuery.data ?? []).length === 0}
            dqChecks={opsDqLatestQuery.data ?? []}
            dqError={opsDqLatestQuery.error}
            dqLoading={opsDqLatestQuery.isLoading && (opsDqLatestQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'quant-fase0' ? (
          <QuantPhase0Tab
            summary={quantInventorySummaryQuery.data}
            summaryError={quantInventorySummaryQuery.error}
            summaryLoading={quantInventorySummaryQuery.isLoading && !quantInventorySummaryQuery.data}
            coverage={quantTickerCoverageQuery.data ?? []}
            coverageError={quantTickerCoverageQuery.error}
            coverageLoading={quantTickerCoverageQuery.isLoading && (quantTickerCoverageQuery.data ?? []).length === 0}
            incidents={quantDataQualityIncidentsQuery.data ?? []}
            incidentsError={quantDataQualityIncidentsQuery.error}
            incidentsLoading={quantDataQualityIncidentsQuery.isLoading && (quantDataQualityIncidentsQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'neural-training-data' ? (
          <NeuralTrainingDataTab
            allocation={neuralTrainingDataAllocationQuery.data ?? []}
            allocationError={neuralTrainingDataAllocationQuery.error}
            allocationLoading={neuralTrainingDataAllocationQuery.isLoading && (neuralTrainingDataAllocationQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'neural-training-runs' ? (
          <NeuralTrainingRunsTab
            runs={neuralTrainingRunsQuery.data ?? []}
            runsError={neuralTrainingRunsQuery.error}
            runsLoading={neuralTrainingRunsQuery.isLoading && (neuralTrainingRunsQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'neural-evolution' ? (
          <NeuralEvolutionTab
            leaderboard={neuralEvolutionLeaderboardQuery.data ?? []}
            leaderboardError={neuralEvolutionLeaderboardQuery.error}
            leaderboardLoading={neuralEvolutionLeaderboardQuery.isLoading && (neuralEvolutionLeaderboardQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'ai-advisor' ? (
          <AiAdvisorTab leaderboard={neuralEvolutionLeaderboardQuery.data ?? []} />
        ) : null}

        {activeTab === 'sinais' ? (
          <SinaisTab
            signalsNext={opsSignalsNextQuery.data ?? []}
            signalsNextError={opsSignalsNextQuery.error}
            signalsNextLoading={opsSignalsNextQuery.isLoading && (opsSignalsNextQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'incidentes' ? (
          <IncidentesTab
            incidents={opsIncidentsOpenQuery.data ?? []}
            incidentsError={opsIncidentsOpenQuery.error}
            incidentsLoading={opsIncidentsOpenQuery.isLoading && (opsIncidentsOpenQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'backtest' ? (
          <BacktestTab
            trades={opsBacktestTradesQuery.data ?? []}
            error={opsBacktestTradesQuery.error}
            loading={opsBacktestTradesQuery.isLoading && (opsBacktestTradesQuery.data ?? []).length === 0}
          />
        ) : null}

        {activeTab === 'quant-roadmap' ? (
          <QuantRoadmapTab
            selectedKey={selectedRoadmapKey}
            baselineStrategies={quantBaselineStrategiesQuery.data ?? []}
            baselineStrategiesError={quantBaselineStrategiesQuery.error}
            baselineStrategiesLoading={quantBaselineStrategiesQuery.isLoading && (quantBaselineStrategiesQuery.data ?? []).length === 0}
            baselineAlerts={quantStrategyDetailAlertsQuery.data ?? []}
            baselineAlertsError={quantStrategyDetailAlertsQuery.error}
            baselineAlertsLoading={quantStrategyDetailAlertsQuery.isLoading && (quantStrategyDetailAlertsQuery.data ?? []).length === 0}
            rankingDaily={quantRankingDailyQuery.data ?? []}
            rankingDailyError={quantRankingDailyQuery.error}
            rankingDailyLoading={quantRankingDailyQuery.isLoading && (quantRankingDailyQuery.data ?? []).length === 0}
            rankingPerformance={quantRankingPerformanceQuery.data ?? []}
            rankingPerformanceError={quantRankingPerformanceQuery.error}
            rankingPerformanceLoading={quantRankingPerformanceQuery.isLoading && (quantRankingPerformanceQuery.data ?? []).length === 0}
            marketRegime={quantMarketRegimeQuery.data ?? []}
            marketRegimeError={quantMarketRegimeQuery.error}
            marketRegimeLoading={quantMarketRegimeQuery.isLoading && (quantMarketRegimeQuery.data ?? []).length === 0}
            exposureRecommendations={quantExposureRecommendationsQuery.data ?? []}
            exposureRecommendationsError={quantExposureRecommendationsQuery.error}
            exposureRecommendationsLoading={quantExposureRecommendationsQuery.isLoading && (quantExposureRecommendationsQuery.data ?? []).length === 0}
            strategyRegimePerformance={quantStrategyRegimePerformanceQuery.data ?? []}
            strategyRegimePerformanceError={quantStrategyRegimePerformanceQuery.error}
            strategyRegimePerformanceLoading={quantStrategyRegimePerformanceQuery.isLoading && (quantStrategyRegimePerformanceQuery.data ?? []).length === 0}
            filterEffectiveness={quantFilterEffectivenessQuery.data ?? []}
            filterEffectivenessError={quantFilterEffectivenessQuery.error}
            filterEffectivenessLoading={quantFilterEffectivenessQuery.isLoading && (quantFilterEffectivenessQuery.data ?? []).length === 0}
            robustness={quantRobustnessQuery.data ?? { strategies: [], walkForward: [], parameterSensitivity: [], costStressTests: [] }}
            robustnessError={quantRobustnessQuery.error}
            robustnessLoading={quantRobustnessQuery.isLoading && !quantRobustnessQuery.data}
            paperTrading={quantPaperTradingQuery.data ?? { dashboard: null, openOrders: [], closedOrders: [], diary: [] }}
            paperTradingError={quantPaperTradingQuery.error}
            paperTradingLoading={quantPaperTradingQuery.isLoading && !quantPaperTradingQuery.data}
            committee={quantCommitteeQuery.data ?? { strategies: [], riskLimits: [], exposureSnapshots: [] }}
            committeeError={quantCommitteeQuery.error}
            committeeLoading={quantCommitteeQuery.isLoading && !quantCommitteeQuery.data}
          />
        ) : null}
          </Box>
        </Box>
      </Container>
    </Box>
  )
}

export default App
