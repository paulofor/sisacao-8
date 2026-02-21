import {
  Alert,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { type FC, type FormEvent, useEffect, useMemo, useState } from 'react'

import type { OpsSignalHistoryEntry, OpsSignalNext, OpsSignalsHistoryFilters } from '../../api/ops'
import SignalsHistoryTable from '../ops/SignalsHistoryTable'
import SignalsNextTable from '../ops/SignalsNextTable'

interface SinaisTabProps {
  signalsNext: OpsSignalNext[]
  signalsNextError?: Error | null
  signalsNextLoading: boolean
  signalsHistory: OpsSignalHistoryEntry[]
  signalsHistoryError?: Error | null
  signalsHistoryLoading: boolean
  historyFilters: OpsSignalsHistoryFilters
  onHistoryFiltersChange: (filters: OpsSignalsHistoryFilters) => void
}

const SinaisTab: FC<SinaisTabProps> = ({
  signalsNext,
  signalsNextError,
  signalsNextLoading,
  signalsHistory,
  signalsHistoryError,
  signalsHistoryLoading,
  historyFilters,
  onHistoryFiltersChange,
}) => {
  const [tickerFilter, setTickerFilter] = useState('')
  const [sideFilter, setSideFilter] = useState<'all' | 'BUY' | 'SELL'>('all')
  const [historyForm, setHistoryForm] = useState({
    from: historyFilters.from,
    to: historyFilters.to,
    limit: historyFilters.limit?.toString() ?? '',
  })
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    setHistoryForm({
      from: historyFilters.from,
      to: historyFilters.to,
      limit: historyFilters.limit?.toString() ?? '',
    })
  }, [historyFilters])

  const filteredNextSignals = useMemo(() => {
    return signalsNext.filter((signal) => {
      const matchesTicker = tickerFilter ? signal.ticker.toLowerCase().includes(tickerFilter.toLowerCase()) : true
      const matchesSide = sideFilter === 'all' ? true : signal.side?.toUpperCase() === sideFilter
      return matchesTicker && matchesSide
    })
  }, [signalsNext, tickerFilter, sideFilter])

  const handleHistoryFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)

    const { from, to, limit } = historyForm
    if (!from || !to) {
      setFormError('Informe as datas inicial e final para buscar o histórico.')
      return
    }

    if (dayjs(from).isAfter(dayjs(to))) {
      setFormError('A data inicial não pode ser maior que a final.')
      return
    }

    const parsedLimit = limit ? Number.parseInt(limit, 10) : undefined
    if (parsedLimit !== undefined && (!Number.isFinite(parsedLimit) || parsedLimit <= 0)) {
      setFormError('O limite deve ser um número positivo.')
      return
    }

    onHistoryFiltersChange({ from, to, limit: parsedLimit })
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Sinais — Próximo Pregão e Histórico
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Visualize os top 5 sinais gerados para o próximo pregão e pesquise históricos anteriores filtrando por período e
          quantidade máxima de registros.
        </Typography>
      </Stack>

      <Paper
        elevation={0}
        sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}
      >
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Filtros — Próximo Pregão
        </Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            label="Ticker"
            value={tickerFilter}
            onChange={(event) => setTickerFilter(event.target.value)}
            placeholder="Ex.: PETR4"
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel id="signals-side-filter">Side</InputLabel>
            <Select
              labelId="signals-side-filter"
              label="Side"
              value={sideFilter}
              onChange={(event) => setSideFilter(event.target.value as typeof sideFilter)}
            >
              <MenuItem value="all">Todos</MenuItem>
              <MenuItem value="BUY">BUY</MenuItem>
              <MenuItem value="SELL">SELL</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      <SignalsNextTable signals={filteredNextSignals} isLoading={signalsNextLoading} error={signalsNextError} />

      <Paper
        elevation={0}
        sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}
      >
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Histórico — Período
        </Typography>
        <Stack component="form" spacing={2} direction={{ xs: 'column', md: 'row' }} onSubmit={handleHistoryFormSubmit}>
          <TextField
            label="Data inicial"
            type="date"
            value={historyForm.from}
            onChange={(event) => setHistoryForm((prev) => ({ ...prev, from: event.target.value }))}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Data final"
            type="date"
            value={historyForm.to}
            onChange={(event) => setHistoryForm((prev) => ({ ...prev, to: event.target.value }))}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Limite"
            type="number"
            value={historyForm.limit}
            onChange={(event) => setHistoryForm((prev) => ({ ...prev, limit: event.target.value }))}
            InputProps={{ inputProps: { min: 1, step: 10 } }}
            placeholder="Máx. de linhas"
            fullWidth
          />
          <Button type="submit" variant="contained" color="primary" disabled={signalsHistoryLoading} sx={{ minWidth: 180 }}>
            Aplicar filtros
          </Button>
        </Stack>
        {formError ? (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {formError}
          </Alert>
        ) : null}
      </Paper>

      <SignalsHistoryTable signals={signalsHistory} isLoading={signalsHistoryLoading} error={signalsHistoryError} />
    </Stack>
  )
}

export default SinaisTab
