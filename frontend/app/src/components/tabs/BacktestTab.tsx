import { Stack, Typography } from '@mui/material'
import type { FC } from 'react'
import type { OpsBacktestTrade } from '../../api/ops'
import BacktestTradesTable from '../ops/BacktestTradesTable'

interface Props { trades: OpsBacktestTrade[]; loading: boolean; error?: Error | null }

const BacktestTab: FC<Props> = ({ trades, loading, error }) => (
  <Stack spacing={2}>
    <Typography variant="h4">Backtest</Typography>
    <Typography variant="body2" color="text.secondary">Últimos 50 trades registrados no backtest diário.</Typography>
    <BacktestTradesTable trades={trades} loading={loading} error={error} />
  </Stack>
)

export default BacktestTab
