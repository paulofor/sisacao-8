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
  const maxCount = Math.max(...buckets.map((bucket) => bucket.count), 1)

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Typography variant="h6">Distribuição de resultados do backtest</Typography>
        <Typography variant="body2" color="text.secondary">
          Uma barra por resultado (target, stop, expired, etc.) usando os trades carregados.
        </Typography>

        {buckets.map((bucket) => {
          const widthPercent = (bucket.count / maxCount) * 100

          return (
            <Box key={bucket.label}>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>{bucket.label}</Typography>
                <Typography variant="body2" color="text.secondary">{bucket.count}</Typography>
              </Stack>
              <Box sx={{ height: 18, borderRadius: 1, bgcolor: 'action.hover', overflow: 'hidden' }}>
                <Box
                  sx={{
                    height: '100%',
                    width: `${widthPercent}%`,
                    minWidth: widthPercent > 0 ? '6px' : 0,
                    borderRadius: 1,
                    bgcolor: 'primary.main',
                    transition: 'width 0.3s ease'
                  }}
                />
              </Box>
            </Box>
          )
        })}
      </Stack>
    </Paper>
  )
}

export default BacktestOutcomesBarChart
