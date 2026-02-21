import {
  Alert,
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { FC } from 'react'

import type {
  DataCollectionMessage,
  DataCollectionMessageSeverity,
  IntradayDailyCount,
  IntradayLatestRecord,
  IntradaySummary,
} from '../../api/dataCollections'
import DataCollectionMessagesTable from '../DataCollectionMessagesTable'
import IntradayDailyCountsCard from '../IntradayDailyCountsCard'
import IntradayLatestRecordsCard from '../IntradayLatestRecordsCard'
import IntradaySummaryCard from '../IntradaySummaryCard'

interface ColetasTabProps {
  severityOptions: Array<'all' | DataCollectionMessageSeverity>
  selectedSeverity: 'all' | DataCollectionMessageSeverity
  onSeverityChange: (value: 'all' | DataCollectionMessageSeverity) => void
  searchTerm: string
  onSearchTermChange: (value: string) => void
  messages: DataCollectionMessage[]
  messagesError?: Error | null
  intradaySummary?: IntradaySummary
  intradaySummaryError?: Error | null
  intradaySummaryLoading: boolean
  intradayDailyCounts?: IntradayDailyCount[]
  intradayDailyCountsError?: Error | null
  intradayDailyCountsLoading: boolean
  intradayLatestRecords?: IntradayLatestRecord[]
  intradayLatestRecordsError?: Error | null
  intradayLatestRecordsLoading: boolean
}

const ColetasTab: FC<ColetasTabProps> = ({
  severityOptions,
  selectedSeverity,
  onSeverityChange,
  searchTerm,
  onSearchTermChange,
  messages,
  messagesError,
  intradaySummary,
  intradaySummaryError,
  intradaySummaryLoading,
  intradayDailyCounts,
  intradayDailyCountsError,
  intradayDailyCountsLoading,
  intradayLatestRecords,
  intradayLatestRecordsError,
  intradayLatestRecordsLoading,
}) => {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" gutterBottom color="text.primary">
          Mensagens das Coletas de Dados
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Consulte em tempo real os registros inseridos pelas pipelines de ingestão no BigQuery. Utilize os filtros para
          encontrar rapidamente coletas específicas ou investigar eventuais falhas.
        </Typography>
      </Box>

      <IntradaySummaryCard summary={intradaySummary} isLoading={intradaySummaryLoading} error={intradaySummaryError ?? null} />

      <IntradayDailyCountsCard
        counts={intradayDailyCounts}
        isLoading={intradayDailyCountsLoading}
        error={intradayDailyCountsError ?? null}
      />

      <IntradayLatestRecordsCard
        records={intradayLatestRecords}
        isLoading={intradayLatestRecordsLoading}
        error={intradayLatestRecordsError ?? null}
      />

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'stretch', md: 'center' }}>
        <FormControl sx={{ minWidth: { xs: '100%', md: 200 } }} size="small">
          <InputLabel id="severity-select-label">Severidade</InputLabel>
          <Select
            labelId="severity-select-label"
            label="Severidade"
            value={selectedSeverity}
            onChange={(event) => onSeverityChange(event.target.value as typeof selectedSeverity)}
          >
            {severityOptions.map((option) => (
              <MenuItem key={option} value={option}>
                {option === 'all' ? 'Todas' : option}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          size="small"
          label="Buscar por coletor, dataset ou mensagem"
          value={searchTerm}
          onChange={(event) => onSearchTermChange(event.target.value)}
          fullWidth
        />
      </Stack>

      {messagesError ? (
        <Alert severity="error">
          Não foi possível carregar as mensagens. Verifique se a API do backend está disponível e tente novamente.
        </Alert>
      ) : null}

      <DataCollectionMessagesTable messages={messages} />
    </Stack>
  )
}

export default ColetasTab
