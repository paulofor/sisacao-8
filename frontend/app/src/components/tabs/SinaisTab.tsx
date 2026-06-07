import {
  Alert,
  Button,
  Card,
  Chip,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { type FC, type FormEvent, useEffect, useMemo, useState } from 'react'

import type { OpsSignalByDateEntry, OpsSignalHistoryEntry, OpsSignalNext, OpsSignalsHistoryFilters } from '../../api/ops'
import { useOpsSignalsByDate } from '../../hooks/useOpsSignalsByDate'
import PossibleTradesInsights from '../ops/PossibleTradesInsights'
import SignalsNextTable from '../ops/SignalsNextTable'
import { calculateSignalTradeMetrics } from '../ops/signalMetrics'

interface SinaisTabProps {
  signalsNext: OpsSignalNext[]
  signalsNextError?: Error | null
  signalsNextLoading: boolean
  signalsHistory: OpsSignalHistoryEntry[]
  signalsHistoryLoading: boolean
  historyFilters: OpsSignalsHistoryFilters
  onHistoryFiltersChange: (filters: OpsSignalsHistoryFilters) => void
}

const formatPercent = (value: number | null) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `${value.toFixed(2)}%`
  }
  return '—'
}

const formatRatio = (value: number | null) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `${value.toFixed(2)}x`
  }
  return '—'
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const formatPrice = (value: number | null) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return currencyFormatter.format(value)
  }
  return '—'
}

const formatDate = (value: string | null) => {
  if (!value) {
    return '—'
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const signalGeneratedTrade = (signal: OpsSignalByDateEntry): boolean => {
  if (signal.entry === null) {
    return false
  }

  const side = signal.side?.toUpperCase()
  if (side === 'BUY') {
    return signal.nextDayLow !== null && signal.nextDayLow <= signal.entry
  }
  if (side === 'SELL') {
    return signal.nextDayHigh !== null && signal.nextDayHigh >= signal.entry
  }
  return false
}

const SignalsByDateTable: FC<{
  signals: OpsSignalByDateEntry[]
  isLoading: boolean
  error?: Error | null
}> = ({ signals, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Erro ao carregar os sinais da data selecionada.</Alert>
  }

  return (
    <Table size="small" aria-label="Sinais por data com máximo e mínimo do pregão seguinte">
      <TableHead>
        <TableRow>
          <TableCell>Ticker</TableCell>
          <TableCell>Side</TableCell>
          <TableCell>Entry</TableCell>
          <TableCell>Target</TableCell>
          <TableCell>Stop</TableCell>
          <TableCell>Pregão seguinte</TableCell>
          <TableCell>Máximo</TableCell>
          <TableCell>Mínimo</TableCell>
          <TableCell>Score</TableCell>
          <TableCell>Rank</TableCell>
          <TableCell>Trade</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {isLoading && signals.length === 0 ? (
          <TableRow>
            <TableCell colSpan={11} align="center">
              <Typography variant="body2" color="text.secondary">
                Buscando sinais da data...
              </Typography>
            </TableCell>
          </TableRow>
        ) : null}

        {signals.map((signal) => {
          const generatedTrade = signalGeneratedTrade(signal)

          return (
            <TableRow
              key={`${signal.dateRef}-${signal.ticker}-${signal.rank}`}
              hover
              sx={
                generatedTrade
                  ? {
                      '& td': { borderBottomColor: 'success.light' },
                      '&.MuiTableRow-hover:hover': { backgroundColor: '#dff3e2' },
                      backgroundColor: '#edf7ed',
                      boxShadow: 'inset 4px 0 0 #2e7d32',
                    }
                  : undefined
              }
            >
              <TableCell>
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {signal.ticker}
                </Typography>
              </TableCell>
              <TableCell>{signal.side}</TableCell>
              <TableCell>{formatPrice(signal.entry)}</TableCell>
              <TableCell>{formatPrice(signal.target)}</TableCell>
              <TableCell>{formatPrice(signal.stop)}</TableCell>
              <TableCell>{formatDate(signal.nextTradingDay ?? signal.validFor)}</TableCell>
              <TableCell>{formatPrice(signal.nextDayHigh)}</TableCell>
              <TableCell>{formatPrice(signal.nextDayLow)}</TableCell>
              <TableCell>{signal.score ?? '—'}</TableCell>
              <TableCell>{signal.rank ?? '—'}</TableCell>
              <TableCell>
                {generatedTrade ? (
                  <Chip color="success" label="Gerou trade" size="small" variant="filled" />
                ) : (
                  <Chip label="Sem trade" size="small" variant="outlined" />
                )}
              </TableCell>
            </TableRow>
          )
        })}

        {!isLoading && signals.length === 0 ? (
          <TableRow>
            <TableCell colSpan={11} align="center">
              <Typography variant="body2" color="text.secondary">
                Nenhum sinal encontrado para a data selecionada.
              </Typography>
            </TableCell>
          </TableRow>
        ) : null}
      </TableBody>
    </Table>
  )
}

const SinaisTab: FC<SinaisTabProps> = ({
  signalsNext,
  signalsNextError,
  signalsNextLoading,
  signalsHistory,
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
  const [signalsByDateForm, setSignalsByDateForm] = useState(dayjs().format('YYYY-MM-DD'))
  const [selectedSignalsDate, setSelectedSignalsDate] = useState(dayjs().format('YYYY-MM-DD'))
  const signalsByDateQuery = useOpsSignalsByDate(selectedSignalsDate)

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

  const summary = useMemo(() => {
    const allSignals = [...filteredNextSignals, ...signalsHistory]

    const aggregated = allSignals.reduce(
      (acc, signal) => {
        const metrics = calculateSignalTradeMetrics(signal.side, signal.entry, signal.target, signal.stop)

        if (
          metrics.upsidePct !== null &&
          metrics.downsidePct !== null &&
          metrics.riskReward !== null &&
          metrics.upsidePct > 0 &&
          metrics.downsidePct > 0
        ) {
          acc.validCount += 1
          acc.upsideSum += metrics.upsidePct
          acc.downsideSum += metrics.downsidePct
          acc.ratioSum += metrics.riskReward
        }

        return acc
      },
      {
        validCount: 0,
        upsideSum: 0,
        downsideSum: 0,
        ratioSum: 0,
      },
    )

    if (aggregated.validCount === 0) {
      return {
        validCount: 0,
        avgUpside: null,
        avgDownside: null,
        avgRatio: null,
      }
    }

    return {
      validCount: aggregated.validCount,
      avgUpside: aggregated.upsideSum / aggregated.validCount,
      avgDownside: aggregated.downsideSum / aggregated.validCount,
      avgRatio: aggregated.ratioSum / aggregated.validCount,
    }
  }, [filteredNextSignals, signalsHistory])

  const handleSignalsByDateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (signalsByDateForm) {
      setSelectedSignalsDate(signalsByDateForm)
    }
  }

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

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Sinais com cálculo válido
              </Typography>
              <Typography variant="h5" color="text.primary" fontWeight={700}>
                {summary.validCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Upside médio potencial
              </Typography>
              <Typography variant="h5" color="success.main" fontWeight={700}>
                {formatPercent(summary.avgUpside)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Risco médio potencial
              </Typography>
              <Typography variant="h5" color="warning.main" fontWeight={700}>
                {formatPercent(summary.avgDownside)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Risco/Retorno médio
              </Typography>
              <Typography variant="h5" color="primary.main" fontWeight={700}>
                {formatRatio(summary.avgRatio)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Alert severity="info">
        A tabela de backtrade ainda está vazia. Nesta tela mostramos o potencial de trade (target/stop) a partir dos sinais,
        até que os resultados realizados estejam disponíveis.
      </Alert>

      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
        <Stack spacing={2}>
          <Stack spacing={0.5}>
            <Typography variant="h6" fontWeight={600}>
              Sinais por data e pregão seguinte
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Escolha a data de geração dos sinais para ver os tickers daquele dia, o máximo/mínimo do pregão seguinte
              e quais sinais acionaram a entrada do trade.
            </Typography>
          </Stack>
          <Stack component="form" direction={{ xs: 'column', md: 'row' }} spacing={2} onSubmit={handleSignalsByDateSubmit}>
            <TextField
              label="Data dos sinais"
              type="date"
              value={signalsByDateForm}
              onChange={(event) => setSignalsByDateForm(event.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={signalsByDateQuery.isFetching || !signalsByDateForm}
              sx={{ minWidth: 180 }}
            >
              Buscar sinais
            </Button>
          </Stack>
          <SignalsByDateTable
            signals={signalsByDateQuery.data ?? []}
            isLoading={signalsByDateQuery.isLoading && !signalsByDateQuery.data}
            error={signalsByDateQuery.error}
          />
        </Stack>
      </Paper>

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

      <PossibleTradesInsights
        signals={filteredNextSignals}
        title="Simulação de possíveis trades — Próximo pregão"
        subtitle="Estimativa baseada nas colunas Entry, Target e Stop da tabela de sinais."
        emptyMessage="Sem sinais do próximo pregão para simular possíveis trades."
      />

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

      <PossibleTradesInsights
        signals={signalsHistory}
        title="Simulação de possíveis trades — Histórico filtrado"
        subtitle="Use este bloco enquanto a tabela de backtrade estiver vazia para entender o potencial dos sinais."
        emptyMessage="Sem histórico no período selecionado para estimar possíveis trades."
      />

    </Stack>
  )
}

export default SinaisTab
