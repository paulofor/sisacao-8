import {
  Alert,
  Button,
  Card,
  Chip,
  CardContent,
  Grid,
  Paper,
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
import { type FC, type FormEvent, useMemo, useState } from 'react'

import type { OpsSignalByDateEntry, OpsSignalNext } from '../../api/ops'
import { useOpsSignalsByDate } from '../../hooks/useOpsSignalsByDate'
import SignalsNextTable from '../ops/SignalsNextTable'
import { calculateSignalTradeMetrics } from '../ops/signalMetrics'

interface SinaisTabProps {
  signalsNext: OpsSignalNext[]
  signalsNextError?: Error | null
  signalsNextLoading: boolean
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
}) => {
  const [signalsByDateForm, setSignalsByDateForm] = useState(dayjs().format('YYYY-MM-DD'))
  const [selectedSignalsDate, setSelectedSignalsDate] = useState(dayjs().format('YYYY-MM-DD'))
  const signalsByDateQuery = useOpsSignalsByDate(selectedSignalsDate)

  const summary = useMemo(() => {
    const allSignals = signalsNext

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
  }, [signalsNext])

  const handleSignalsByDateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (signalsByDateForm) {
      setSelectedSignalsDate(signalsByDateForm)
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Sinais — Próximo Pregão e Histórico
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Visualize os top 5 sinais gerados para o próximo pregão e consulte sinais por data com o máximo/mínimo do
          pregão seguinte.
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

      <SignalsNextTable signals={signalsNext} isLoading={signalsNextLoading} error={signalsNextError} />
    </Stack>
  )
}

export default SinaisTab
