import RefreshIcon from '@mui/icons-material/Refresh'
import {
  Alert,
  AppBar,
  Box,
  Button,
  Container,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'

import type { DataCollectionMessage, DataCollectionMessageSeverity } from './api/dataCollections'
import DataCollectionMessagesTable from './components/DataCollectionMessagesTable'
import { useDataCollectionMessages } from './hooks/useDataCollectionMessages'

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

function App() {
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | DataCollectionMessageSeverity>('all')
  const [searchTerm, setSearchTerm] = useState('')

  const { data, isLoading, isFetching, refetch, error, dataUpdatedAt } = useDataCollectionMessages({
    severity: selectedSeverity === 'all' ? undefined : selectedSeverity,
  })

  const messages = data ?? []

  const filteredMessages = useMemo(
    () => filterMessagesBySearch(messages, searchTerm),
    [messages, searchTerm],
  )

  const lastUpdatedLabel = dataUpdatedAt
    ? `Atualizado às ${dayjs(dataUpdatedAt).format('HH:mm:ss')}`
    : 'Aguardando atualização'

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" color="transparent" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Typography variant="h6" color="text.primary" sx={{ flexGrow: 1 }}>
            Monitoramento de Coletas – BigQuery
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {lastUpdatedLabel}
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={() => {
              void refetch()
            }}
            disabled={isFetching}
          >
            Atualizar
          </Button>
        </Toolbar>
        {isLoading || isFetching ? <LinearProgress color="primary" /> : null}
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
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

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'stretch', md: 'center' }}>
            <FormControl sx={{ minWidth: { xs: '100%', md: 200 } }} size="small">
              <InputLabel id="severity-select-label">Severidade</InputLabel>
              <Select
                labelId="severity-select-label"
                label="Severidade"
                value={selectedSeverity}
                onChange={(event) => setSelectedSeverity(event.target.value as typeof selectedSeverity)}
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
              onChange={(event) => setSearchTerm(event.target.value)}
              fullWidth
            />
          </Stack>

          {error ? (
            <Alert severity="error">
              Não foi possível carregar as mensagens. Verifique se a API do backend está disponível e tente novamente.
            </Alert>
          ) : null}

          <DataCollectionMessagesTable messages={filteredMessages} />
        </Stack>
      </Container>
    </Box>
  )
}

export default App

