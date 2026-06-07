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

const outcomeStyles = (outcome: string | null | undefined) => {
  const normalized = (outcome ?? '').toUpperCase()
  if (normalized === 'STOP') {
    return {
      color: 'error.main',
      borderLeft: '3px solid',
      borderLeftColor: 'error.main',
      fontWeight: 600
    }
  }

  if (normalized.includes('TARGET')) {
    return {
      color: 'info.main',
      borderLeft: '3px solid',
      borderLeftColor: 'info.main',
      fontWeight: 600
    }
  }

  return undefined
}

const MAX_VISIBLE_TRADES = 10

const BacktestTradesTable: FC<Props> = ({ trades, loading, error }) => {
  if (error) return <Alert severity="error">Falha ao carregar trades de backtest: {error.message}</Alert>
  if (!loading && trades.length === 0) return <Alert severity="info">Sem trades de backtest.</Alert>

  const visibleTrades = trades.slice(0, MAX_VISIBLE_TRADES)

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table
        size="small"
        sx={{
          tableLayout: 'fixed',
          '& .MuiTableCell-root': {
            fontSize: '0.8rem',
            py: 0.6
          }
        }}
      >
        <TableHead>
          <TableRow>
            <TableCell>Data Ref</TableCell><TableCell>Ticker</TableCell><TableCell>Side</TableCell><TableCell>Dt Entrada</TableCell><TableCell align="right">Preço Entrada</TableCell><TableCell>Dt Saída</TableCell><TableCell align="right">Preço Saída</TableCell><TableCell align="right">Qtde Dias</TableCell><TableCell align="right">Preço Limite</TableCell><TableCell align="right">Score Entrada</TableCell><TableCell align="right">Entry</TableCell><TableCell align="right">Exit</TableCell><TableCell align="right">PnL %</TableCell><TableCell>Outcome</TableCell><TableCell>Criado em</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {visibleTrades.map((t, i) => (
            <TableRow key={`${t.ticker}-${t.dateRef}-${i}`}>
              <TableCell sx={{ minWidth: 84, whiteSpace: 'nowrap' }}>{t.dateRef ?? '—'}</TableCell><TableCell>{t.ticker}</TableCell><TableCell>{t.side}</TableCell><TableCell sx={{ minWidth: 84, whiteSpace: 'nowrap' }}>{t.entryDate ?? '—'}</TableCell><TableCell align="right">{fmt(t.entryPrice)}</TableCell><TableCell sx={{ minWidth: 84, whiteSpace: 'nowrap' }}>{t.exitDate ?? '—'}</TableCell><TableCell align="right">{fmt(t.exitPrice)}</TableCell><TableCell align="right">{t.daysInTrade ?? '—'}</TableCell><TableCell align="right">{fmt(t.entryLimitPrice)}</TableCell><TableCell align="right">{fmt(t.entrySignalScore)}</TableCell><TableCell align="right">{fmt(t.entry)}</TableCell><TableCell align="right">{fmt(t.exit)}</TableCell><TableCell align="right">{fmt(t.pnlPct)}</TableCell><TableCell sx={outcomeStyles(t.outcome)}>{t.outcome ?? '—'}</TableCell><TableCell sx={{ minWidth: 132, whiteSpace: 'nowrap' }}>{t.createdAt ? dayjs(t.createdAt).format('YYYY-MM-DD HH:mm') : '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Typography variant="caption" sx={{ p: 1, display: 'block' }}>Mostrando os {visibleTrades.length} trades mais recentes.</Typography>
    </TableContainer>
  )
}

export default BacktestTradesTable
