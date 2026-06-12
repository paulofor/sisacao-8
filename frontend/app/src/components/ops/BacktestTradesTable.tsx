import {
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow
} from '@mui/material'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState, type FC } from 'react'

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

const TRADES_PER_PAGE = 25

const BacktestTradesTable: FC<Props> = ({ trades, loading, error }) => {
  const [page, setPage] = useState(0)

  useEffect(() => {
    setPage(0)
  }, [trades])

  const visibleTrades = useMemo(() => {
    const start = page * TRADES_PER_PAGE
    return trades.slice(start, start + TRADES_PER_PAGE)
  }, [page, trades])

  if (error) return <Alert severity="error">Falha ao carregar trades de backtest: {error.message}</Alert>
  if (!loading && trades.length === 0) return <Alert severity="info">Sem trades de backtest.</Alert>

  return (
    <Paper variant="outlined" sx={{ maxWidth: '100%', overflow: 'hidden' }}>
      <TableContainer sx={{ maxWidth: '100%', overflowX: 'hidden' }}>
        <Table
          size="small"
          sx={{
            width: '100%',
            tableLayout: 'fixed',
            '& .MuiTableCell-root': {
              fontSize: '0.75rem',
              lineHeight: 1.25,
              overflow: 'hidden',
              overflowWrap: 'anywhere',
              px: 0.75,
              py: 0.6,
              textOverflow: 'ellipsis',
              wordBreak: 'break-word'
            },
            '& .MuiTableCell-head': {
              fontSize: '0.72rem',
              fontWeight: 700
            }
          }}
        >
          <TableHead>
            <TableRow>
              <TableCell>Data Ref</TableCell>
              <TableCell>Ticker</TableCell>
              <TableCell>Side</TableCell>
              <TableCell>Dt Entrada</TableCell>
              <TableCell align="right">Preço Entrada</TableCell>
              <TableCell>Dt Saída</TableCell>
              <TableCell align="right">Preço Saída</TableCell>
              <TableCell align="right">Qtde Dias</TableCell>
              <TableCell align="right">Preço Limite</TableCell>
              <TableCell align="right">Score Entrada</TableCell>
              <TableCell align="right">Entry</TableCell>
              <TableCell align="right">Exit</TableCell>
              <TableCell align="right">PnL %</TableCell>
              <TableCell>Outcome</TableCell>
              <TableCell>Criado em</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleTrades.map((t, i) => (
              <TableRow key={`${t.ticker}-${t.dateRef}-${page}-${i}`}>
                <TableCell>{t.dateRef ?? '—'}</TableCell>
                <TableCell>{t.ticker}</TableCell>
                <TableCell>{t.side}</TableCell>
                <TableCell>{t.entryDate ?? '—'}</TableCell>
                <TableCell align="right">{fmt(t.entryPrice)}</TableCell>
                <TableCell>{t.exitDate ?? '—'}</TableCell>
                <TableCell align="right">{fmt(t.exitPrice)}</TableCell>
                <TableCell align="right">{t.daysInTrade ?? '—'}</TableCell>
                <TableCell align="right">{fmt(t.entryLimitPrice)}</TableCell>
                <TableCell align="right">{fmt(t.entrySignalScore)}</TableCell>
                <TableCell align="right">{fmt(t.entry)}</TableCell>
                <TableCell align="right">{fmt(t.exit)}</TableCell>
                <TableCell align="right">{fmt(t.pnlPct)}</TableCell>
                <TableCell sx={outcomeStyles(t.outcome)}>{t.outcome ?? '—'}</TableCell>
                <TableCell>{t.createdAt ? dayjs(t.createdAt).format('YYYY-MM-DD HH:mm') : '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={trades.length}
        labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
        labelRowsPerPage="Itens por página"
        onPageChange={(_, nextPage) => setPage(nextPage)}
        page={page}
        rowsPerPage={TRADES_PER_PAGE}
        rowsPerPageOptions={[TRADES_PER_PAGE]}
      />
    </Paper>
  )
}

export default BacktestTradesTable
