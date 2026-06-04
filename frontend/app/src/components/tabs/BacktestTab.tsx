import { Card, CardContent, LinearProgress, Stack, Typography } from '@mui/material'
import type { FC } from 'react'
import type { OpsBacktestTrade } from '../../api/ops'
import BacktestOutcomesBarChart from '../ops/BacktestOutcomesBarChart'
import { isExecutedBacktestTrade } from '../ops/backtestTradeFilters'
import BacktestTradesTable from '../ops/BacktestTradesTable'

interface Props { trades: OpsBacktestTrade[]; loading: boolean; error?: Error | null }

const BACKTEST_STATISTICAL_TARGET = 500

const BacktestTab: FC<Props> = ({ trades, loading, error }) => {
  const closedTrades = trades.filter(isExecutedBacktestTrade).length
  const targetPercentage = Math.min((closedTrades / BACKTEST_STATISTICAL_TARGET) * 100, 100)
  const targetPercentageLabel = `${targetPercentage.toFixed(1)}%`

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Backtest</Typography>
      <Typography variant="body2" color="text.secondary">
        Trades mais recentes do backtest diário (até 200 registros por consulta).
      </Typography>
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={1.25}>
            <Typography variant="h6">Validade estatística</Typography>
            <Typography variant="body2" color="text.secondary">
              Trades executados: <strong>{closedTrades}</strong> de {BACKTEST_STATISTICAL_TARGET} meta.
            </Typography>
            <LinearProgress
              aria-label="Percentual da meta de trades executados"
              variant="determinate"
              value={targetPercentage}
            />
            <Typography variant="body2" color="text.secondary">
              Percentual da meta: <strong>{targetPercentageLabel}</strong>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
      <BacktestOutcomesBarChart trades={trades} loading={loading} error={error} />
      <BacktestTradesTable trades={trades} loading={loading} error={error} />
    </Stack>
  )
}

export default BacktestTab
