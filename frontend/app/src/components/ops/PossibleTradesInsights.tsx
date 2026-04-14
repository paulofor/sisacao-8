import {
  Alert,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import type { FC } from 'react'

import type { OpsSignalNext } from '../../api/ops'

interface PossibleTradesInsightsProps {
  signals: OpsSignalNext[]
  title: string
  subtitle: string
  emptyMessage: string
}

interface TradeScenario {
  ticker: string
  side: string
  entry: number
  target: number
  stop: number
  targetReturnPct: number
  stopRiskPct: number
  riskReward: number
}

const percentFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const ratioFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const isFiniteNumber = (value: number | null): value is number => {
  return typeof value === 'number' && Number.isFinite(value)
}

const toTradeScenario = (signal: OpsSignalNext): TradeScenario | null => {
  if (!isFiniteNumber(signal.entry) || !isFiniteNumber(signal.target) || !isFiniteNumber(signal.stop) || signal.entry <= 0) {
    return null
  }

  const side = signal.side?.toUpperCase()
  const isSell = side === 'SELL'

  const targetDelta = isSell ? signal.entry - signal.target : signal.target - signal.entry
  const stopDelta = isSell ? signal.stop - signal.entry : signal.entry - signal.stop

  if (stopDelta <= 0) {
    return null
  }

  const targetReturnPct = targetDelta / signal.entry
  const stopRiskPct = stopDelta / signal.entry

  return {
    ticker: signal.ticker,
    side: side ?? '—',
    entry: signal.entry,
    target: signal.target,
    stop: signal.stop,
    targetReturnPct,
    stopRiskPct,
    riskReward: targetReturnPct / stopRiskPct,
  }
}

const formatPercent = (value: number) => percentFormatter.format(value)

const formatRatio = (value: number) => `${ratioFormatter.format(value)}x`

const PossibleTradesInsights: FC<PossibleTradesInsightsProps> = ({ signals, title, subtitle, emptyMessage }) => {
  const scenarios = signals
    .map(toTradeScenario)
    .filter((scenario): scenario is TradeScenario => scenario !== null)
    .sort((a, b) => b.riskReward - a.riskReward)

  if (signals.length === 0) {
    return <Alert severity="info">{emptyMessage}</Alert>
  }

  if (scenarios.length === 0) {
    return (
      <Alert severity="warning">
        Não foi possível simular trades porque os sinais não possuem Entry/Target/Stop completos.
      </Alert>
    )
  }

  const averageTarget = scenarios.reduce((sum, scenario) => sum + scenario.targetReturnPct, 0) / scenarios.length
  const averageRisk = scenarios.reduce((sum, scenario) => sum + scenario.stopRiskPct, 0) / scenarios.length
  const averageRiskReward = scenarios.reduce((sum, scenario) => sum + scenario.riskReward, 0) / scenarios.length

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
      <Stack spacing={2}>
        <Stack spacing={0.5}>
          <Typography variant="h6" fontWeight={600}>
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="overline" color="text.secondary">
              Retorno alvo médio
            </Typography>
            <Typography variant="h6">{formatPercent(averageTarget)}</Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="overline" color="text.secondary">
              Risco de stop médio
            </Typography>
            <Typography variant="h6">{formatPercent(averageRisk)}</Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="overline" color="text.secondary">
              Relação risco/retorno média
            </Typography>
            <Typography variant="h6">{formatRatio(averageRiskReward)}</Typography>
          </Paper>
        </Stack>

        <Table size="small" aria-label={`${title} - cenários`}>
          <TableHead>
            <TableRow>
              <TableCell>Ticker</TableCell>
              <TableCell>Side</TableCell>
              <TableCell>Retorno alvo</TableCell>
              <TableCell>Risco de stop</TableCell>
              <TableCell>Risco/Retorno</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scenarios.slice(0, 8).map((scenario) => (
              <TableRow key={`${title}-${scenario.ticker}-${scenario.side}`} hover>
                <TableCell>{scenario.ticker}</TableCell>
                <TableCell>{scenario.side}</TableCell>
                <TableCell>{formatPercent(scenario.targetReturnPct)}</TableCell>
                <TableCell>{formatPercent(scenario.stopRiskPct)}</TableCell>
                <TableCell>{formatRatio(scenario.riskReward)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Stack>
    </Paper>
  )
}

export default PossibleTradesInsights
