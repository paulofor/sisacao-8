import { Alert, Box, Paper, Stack, Typography } from '@mui/material'
import type { FC, ReactNode } from 'react'

import type { OpsBacktestTrade } from '../../api/ops'
import { isExecutedBacktestTrade, normalizeBacktestOutcome } from './backtestTradeFilters'

interface Props {
  trades: OpsBacktestTrade[]
  loading: boolean
  error?: Error | null
}

interface OutcomeBucket {
  label: string
  count: number
  color: string
}

const OUTCOME_SLICE_COLORS: Record<string, string> = {
  EXPIRE: '#1976d2',
  EXPIRED: '#1976d2',
  TARGET: '#2e7d32',
  STOP: '#d32f2f',
  UNKNOWN: '#6d4c41',
}
const FALLBACK_SLICE_COLORS = ['#9c27b0', '#0288d1', '#6d4c41']
const PROFIT_LOSS_SLICE_COLORS = {
  profit: '#2e7d32',
  loss: '#d32f2f',
}
const EXECUTION_SLICE_COLORS = {
  executed: '#2e7d32',
  notExecuted: '#f57c00',
}

const toOutcomeLabel = (outcome: string): string => {
  const labels: Record<string, string> = {
    TARGET: 'Target',
    STOP: 'Stop',
    EXPIRED: 'Expired',
    EXPIRE: 'Expire',
    UNKNOWN: 'Sem resultado',
  }

  return labels[outcome] ?? outcome
}

const buildBuckets = (trades: OpsBacktestTrade[]): OutcomeBucket[] => {
  const counts = new Map<string, number>()

  for (const trade of trades) {
    const outcome = normalizeBacktestOutcome(trade.outcome)
    counts.set(outcome, (counts.get(outcome) ?? 0) + 1)
  }

  return Array.from(counts.entries())
    .map(([outcome, count], index) => ({
      label: toOutcomeLabel(outcome),
      count,
      color: OUTCOME_SLICE_COLORS[outcome] ?? FALLBACK_SLICE_COLORS[index % FALLBACK_SLICE_COLORS.length],
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, 'pt-BR'))
}

const buildExecutionBuckets = (trades: OpsBacktestTrade[]): OutcomeBucket[] => {
  const executedCount = trades.filter(isExecutedBacktestTrade).length
  const notExecutedCount = trades.length - executedCount

  return [
    { label: 'Geraram trade', count: executedCount, color: EXECUTION_SLICE_COLORS.executed },
    { label: 'Não geraram trade', count: notExecutedCount, color: EXECUTION_SLICE_COLORS.notExecuted },
  ].filter((bucket) => bucket.count > 0)
}

const buildProfitLossBuckets = (trades: OpsBacktestTrade[]): OutcomeBucket[] => {
  const profitLossBuckets = [
    { label: 'Lucro', count: 0, color: PROFIT_LOSS_SLICE_COLORS.profit },
    { label: 'Prejuízo', count: 0, color: PROFIT_LOSS_SLICE_COLORS.loss },
  ]

  for (const trade of trades) {
    if (trade.pnlPct === null) {
      continue
    }

    const bucketIndex = trade.pnlPct > 0 ? 0 : 1
    profitLossBuckets[bucketIndex].count += 1
  }

  return profitLossBuckets.filter((bucket) => bucket.count > 0)
}

const buildPieBackground = (buckets: OutcomeBucket[], totalCount: number): string => {
  let startPercent = 0
  const gradientParts = buckets.map((bucket) => {
    const slicePercent = (bucket.count / totalCount) * 100
    const endPercent = startPercent + slicePercent
    const segment = `${bucket.color} ${startPercent.toFixed(2)}% ${endPercent.toFixed(2)}%`
    startPercent = endPercent
    return segment
  })

  return `conic-gradient(${gradientParts.join(', ')})`
}

const renderPieChart = (
  title: string,
  description: string,
  buckets: OutcomeBucket[],
  emptyState: ReactNode,
) => {
  const totalCount = buckets.reduce((acc, bucket) => acc + bucket.count, 0)

  if (totalCount === 0) {
    return (
      <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
        <Stack spacing={1.5}>
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
          {emptyState}
        </Stack>
      </Paper>
    )
  }

  const pieBackground = buildPieBackground(buckets, totalCount)

  return (
    <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
      <Stack spacing={1.5} sx={{ height: '100%' }}>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>

        <Stack direction="column" spacing={2} alignItems="center">
          <Box
            sx={{
              width: { xs: 180, sm: 200 },
              height: { xs: 180, sm: 200 },
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
            {buckets.map((bucket) => {
              const percentage = (bucket.count / totalCount) * 100

              return (
                <Stack key={bucket.label} direction="row" justifyContent="space-between" alignItems="center">
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: bucket.color }} />
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

const BacktestOutcomesBarChart: FC<Props> = ({ trades, loading, error }) => {
  if (error) return <Alert severity="error">Falha ao carregar dados do gráfico: {error.message}</Alert>
  if (!loading && trades.length === 0) return <Alert severity="info">Sem trades para montar o gráfico.</Alert>

  const executedTrades = trades.filter(isExecutedBacktestTrade)

  const executionBuckets = buildExecutionBuckets(trades)
  const outcomeBuckets = buildBuckets(executedTrades)
  const profitLossBuckets = buildProfitLossBuckets(executedTrades)

  return (
    <Box
      sx={{
        display: 'grid',
        gap: 2,
        gridTemplateColumns: { xs: '1fr', lg: 'repeat(3, minmax(0, 1fr))' },
        alignItems: 'stretch',
      }}
    >
      {renderPieChart(
        'Sinais que geraram trades',
        'Gráfico de pizza separando os sinais do backtest entre os que acionaram entrada e os que não geraram trade.',
        executionBuckets,
        <Alert severity="info">Carregando sinais para montar o gráfico de geração de trades.</Alert>,
      )}
      {renderPieChart(
        'Distribuição de resultados do backtest',
        'Gráfico de pizza por resultado (target, stop, expire, etc.) considerando apenas trades executados.',
        outcomeBuckets,
        <Alert severity="info">Nenhum trade executado para montar o gráfico de resultados.</Alert>,
      )}
      {renderPieChart(
        'Distribuição de lucro e prejuízo do backtest',
        'Gráfico de pizza por PnL: Lucro quando PnL % é maior que zero e Prejuízo quando PnL % é menor ou igual a zero, incluindo trades que saíram por tempo/expire.',
        profitLossBuckets,
        <Alert severity="info">Nenhum trade executado com PnL informado para montar o gráfico de lucro e prejuízo.</Alert>,
      )}
    </Box>
  )
}

export default BacktestOutcomesBarChart
