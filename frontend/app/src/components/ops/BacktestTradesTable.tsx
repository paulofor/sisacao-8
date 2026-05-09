import { Alert, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { OpsBacktestTrade } from '../../api/ops'

interface Props {
  trades: OpsBacktestTrade[]
  loading: boolean
  error?: Error | null
}

const fmt = (v: number | null | undefined) => (typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : '—')

const BacktestTradesTable: FC<Props> = ({ trades, loading, error }) => {
  if (error) return <Alert severity="error">Falha ao carregar trades de backtest: {error.message}</Alert>
  if (!loading && trades.length === 0) return <Alert severity="info">Sem trades de backtest.</Alert>

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Data Ref</TableCell><TableCell>Ticker</TableCell><TableCell>Side</TableCell><TableCell align="right">Entry</TableCell><TableCell align="right">Exit</TableCell><TableCell align="right">PnL %</TableCell><TableCell>Outcome</TableCell><TableCell>Criado em</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {trades.map((t, i) => (
            <TableRow key={`${t.ticker}-${t.dateRef}-${i}`}>
              <TableCell>{t.dateRef ?? '—'}</TableCell><TableCell>{t.ticker}</TableCell><TableCell>{t.side}</TableCell><TableCell align="right">{fmt(t.entry)}</TableCell><TableCell align="right">{fmt(t.exit)}</TableCell><TableCell align="right">{fmt(t.pnlPct)}</TableCell><TableCell>{t.outcome ?? '—'}</TableCell><TableCell>{t.createdAt ? dayjs(t.createdAt).format('YYYY-MM-DD HH:mm') : '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Typography variant="caption" sx={{ p: 1, display: 'block' }}>Mostrando os {trades.length} trades mais recentes.</Typography>
    </TableContainer>
  )
}

export default BacktestTradesTable
