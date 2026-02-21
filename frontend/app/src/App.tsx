import RefreshIcon from '@mui/icons-material/Refresh'
import {
  AppBar,
  Box,
  Button,
  Container,
  LinearProgress,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from '@mui/material'
import type { UseQueryResult } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { type SyntheticEvent, useMemo, useState } from 'react'

import type { DataCollectionMessage, DataCollectionMessageSeverity } from './api/dataCollections'
import type { OpsSignalHistoryEntry, OpsSignalsHistoryFilters } from './api/ops'
import ColetasTab from './components/tabs/ColetasTab'
import IncidentesTab from './components/tabs/IncidentesTab'
import OperacaoTab from './components/tabs/OperacaoTab'
import SinaisTab from './components/tabs/SinaisTab'
import { useDataCollectionMessages } from './hooks/useDataCollectionMessages'
import { useIntradayDailyCounts } from './hooks/useIntradayDailyCounts'
import { useIntradayLatestRecords } from './hooks/useIntradayLatestRecords'
import { useIntradaySummary } from './hooks/useIntradaySummary'
import { useOpsDqLatest } from './hooks/useOpsDqLatest'
import { useOpsIncidentsOpen } from './hooks/useOpsIncidentsOpen'
import { useOpsOverview } from './hooks/useOpsOverview'
import { useOpsPipeline } from './hooks/useOpsPipeline'
import { useOpsSignalsHistory } from './hooks/useOpsSignalsHistory'
import { useOpsSignalsNext } from './hooks/useOpsSignalsNext'

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

const getDefaultSignalsHistoryFilters = (): OpsSignalsHistoryFilters => {
  return {
    from: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
    to: dayjs().format('YYYY-MM-DD'),
    limit: 100,
  }
}

type TabValue = 'coletas' | 'operacao' | 'sinais' | 'incidentes'

type QueryResult = UseQueryResult<unknown, Error>

function App() {
  const [activeTab, setActiveTab] = useState<TabValue>('coletas')
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | DataCollectionMessageSeverity>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [signalsHistoryFilters, setSignalsHistoryFilters] = useState<OpsSignalsHistoryFilters>(
    getDefaultSignalsHistoryFilters(),
  )

  const dataCollectionMessagesQuery = useDataCollectionMessages({
    severity: selectedSeverity === 'all' ? undefined : selectedSeverity,
  })
  const intradaySummaryQuery = useIntradaySummary()
  const intradayDailyCountsQuery = useIntradayDailyCounts()
  const intradayLatestRecordsQuery = useIntradayLatestRecords()

  const opsOverviewQuery = useOpsOverview()
  const opsPipelineQuery = useOpsPipeline()
  const opsDqLatestQuery = useOpsDqLatest()
  const opsSignalsNextQuery = useOpsSignalsNext()
  const opsSignalsHistoryQuery = useOpsSignalsHistory(signalsHistoryFilters)
  const opsIncidentsOpenQuery = useOpsIncidentsOpen()

  const messages = useMemo(() => dataCollectionMessagesQuery.data ?? [], [dataCollectionMessagesQuery.data])

  const filteredMessages = useMemo(
    () => filterMessagesBySearch(messages, searchTerm),
    [messages, searchTerm],
  )

  const signalsHistoryData = (opsSignalsHistoryQuery.data ?? []) as OpsSignalHistoryEntry[]

  const tabQueries: Record<TabValue, QueryResult[]> = {
    coletas: [
      dataCollectionMessagesQuery,
      intradaySummaryQuery,
      intradayDailyCountsQuery,
      intradayLatestRecordsQuery,
    ] as QueryResult[],
    operacao: [opsOverviewQuery, opsPipelineQuery, opsDqLatestQuery] as QueryResult[],
    sinais: [opsSignalsNextQuery, opsSignalsHistoryQuery] as QueryResult[],
    incidentes: [opsIncidentsOpenQuery] as QueryResult[],
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

  const handleTabChange = (_event: SyntheticEvent, newValue: string | number) => {
    setActiveTab(newValue as TabValue)
  }

  const intradaySummaryLoading = intradaySummaryQuery.isLoading && !intradaySummaryQuery.data
  const intradayDailyCountsLoading = intradayDailyCountsQuery.isLoading && !intradayDailyCountsQuery.data
  const intradayLatestRecordsLoading = intradayLatestRecordsQuery.isLoading && !intradayLatestRecordsQuery.data
  const signalsHistoryLoading = opsSignalsHistoryQuery.isLoading && !opsSignalsHistoryQuery.data

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
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="scrollable"
          allowScrollButtonsMobile
          textColor="primary"
          indicatorColor="primary"
          sx={{ px: 2 }}
        >
          <Tab label="Coletas" value="coletas" />
          <Tab label="Operação" value="operacao" />
          <Tab label="Sinais" value="sinais" />
          <Tab label="Incidentes" value="incidentes" />
        </Tabs>
        {isTabLoading || isRefreshing ? <LinearProgress color="primary" /> : null}
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
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

        {activeTab === 'sinais' ? (
          <SinaisTab
            signalsNext={opsSignalsNextQuery.data ?? []}
            signalsNextError={opsSignalsNextQuery.error}
            signalsNextLoading={opsSignalsNextQuery.isLoading && (opsSignalsNextQuery.data ?? []).length === 0}
            signalsHistory={signalsHistoryData}
            signalsHistoryError={opsSignalsHistoryQuery.error}
            signalsHistoryLoading={signalsHistoryLoading}
            historyFilters={signalsHistoryFilters}
            onHistoryFiltersChange={setSignalsHistoryFilters}
          />
        ) : null}

        {activeTab === 'incidentes' ? (
          <IncidentesTab
            incidents={opsIncidentsOpenQuery.data ?? []}
            incidentsError={opsIncidentsOpenQuery.error}
            incidentsLoading={opsIncidentsOpenQuery.isLoading && (opsIncidentsOpenQuery.data ?? []).length === 0}
          />
        ) : null}
      </Container>
    </Box>
  )
}

export default App
