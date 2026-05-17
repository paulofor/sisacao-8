import { Alert, Box, Paper, Stack, Typography } from '@mui/material'
import type { FC } from 'react'

import type { OpsBacktestTrade } from '../../api/ops'

interface Props {
  trades: OpsBacktestTrade[]
  loading: boolean
  error?: Error | null
}

interface OutcomeBucket {
  label: string
  count: number
}

const SLICE_COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#9c27b0', '#d32f2f', '#0288d1', '#6d4c41']

const normalizeOutcome = (outcome: string | null | undefined): string => {
  const normalized = (outcome ?? '').trim().toUpperCase()
  if (!normalized) {
    return 'UNKNOWN'
  }
  return normalized
}

const toOutcomeLabel = (outcome: string): string => {
  const labels: Record<string, string> = {
    TARGET: 'Target',
    STOP: 'Stop',
    EXPIRED: 'Expired',
    UNKNOWN: 'Sem resultado',
  }

  return labels[outcome] ?? outcome
}

const buildBuckets = (trades: OpsBacktestTrade[]): OutcomeBucket[] => {
  const counts = new Map<string, number>()

  for (const trade of trades) {
    const outcome = normalizeOutcome(trade.outcome)
    counts.set(outcome, (counts.get(outcome) ?? 0) + 1)
  }

  return Array.from(counts.entries())
    .map(([outcome, count]) => ({ label: toOutcomeLabel(outcome), count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, 'pt-BR'))
}

const BacktestOutcomesBarChart: FC<Props> = ({ trades, loading, error }) => {
  if (error) return <Alert severity="error">Falha ao carregar dados do gráfico: {error.message}</Alert>
  if (!loading && trades.length === 0) return <Alert severity="info">Sem trades para montar o gráfico.</Alert>

  const buckets = buildBuckets(trades)
  const totalCount = buckets.reduce((acc, bucket) => acc + bucket.count, 0)

  let startPercent = 0
  const gradientParts = buckets.map((bucket, index) => {
    const slicePercent = (bucket.count / totalCount) * 100
    const endPercent = startPercent + slicePercent
    const color = SLICE_COLORS[index % SLICE_COLORS.length]
    const segment = `${color} ${startPercent.toFixed(2)}% ${endPercent.toFixed(2)}%`
    startPercent = endPercent
    return segment
  })

  const pieBackground = `conic-gradient(${gradientParts.join(', ')})`

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Typography variant="h6">Distribuição de resultados do backtest</Typography>
        <Typography variant="body2" color="text.secondary">
          Gráfico de pizza por resultado (target, stop, expired, etc.) usando os trades carregados.
        </Typography>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
          <Box
            sx={{
              width: 220,
              height: 220,
              borderRadius: '50%',
              background: pieBackground,
              position: 'relative',
              flexShrink: 0,
            }}
          >
            <Box
              sx={{
                position: 'absolute',
                width: 96,
                height: 96,
                borderRadius: '50%',
                bgcolor: 'background.paper',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
              }}
            />
          </Box>

          <Stack spacing={1} sx={{ width: '100%' }}>
            {buckets.map((bucket, index) => {
              const color = SLICE_COLORS[index % SLICE_COLORS.length]
              const percentage = (bucket.count / totalCount) * 100

              return (
                <Stack key={bucket.label} direction="row" justifyContent="space-between" alignItems="center">
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: color }} />
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>{bucket.label}</Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {bucket.count} ({percentage.toFixed(1)}%)
                  </Typography>
                </Stack>
              )
            })}
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  )
}

export default BacktestOutcomesBarChart
