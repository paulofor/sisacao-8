import {
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { OpsSignalHistoryEntry } from '../../api/ops'
import StatusChip from '../StatusChip'

interface SignalsHistoryTableProps {
  signals: OpsSignalHistoryEntry[]
  isLoading: boolean
  error?: Error | null
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

const SignalsHistoryTable: FC<SignalsHistoryTableProps> = ({ signals, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Erro ao carregar o histórico de sinais.</Alert>
  }

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <Typography variant="h6" fontWeight={600} sx={{ p: 3, pb: 0 }}>
        Histórico de Sinais
      </Typography>
      <Table size="small" aria-label="Histórico de sinais">
        <TableHead>
          <TableRow>
            <TableCell>Data Ref.</TableCell>
            <TableCell>Valid for</TableCell>
            <TableCell>Ticker</TableCell>
            <TableCell>Side</TableCell>
            <TableCell>Entry</TableCell>
            <TableCell>Target</TableCell>
            <TableCell>Stop</TableCell>
            <TableCell>Score</TableCell>
            <TableCell>Rank</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading && signals.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} align="center">
                <Typography variant="body2" color="text.secondary">
                  Buscando histórico...
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}

          {signals.map((signal) => (
            <TableRow key={`${signal.dateRef}-${signal.ticker}-${signal.rank}`} hover>
              <TableCell>{formatDate(signal.dateRef)}</TableCell>
              <TableCell>{formatDate(signal.validFor)}</TableCell>
              <TableCell>
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {signal.ticker}
                </Typography>
              </TableCell>
              <TableCell>
                <StatusChip status={signal.side ?? '—'} />
              </TableCell>
              <TableCell>{formatPrice(signal.entry)}</TableCell>
              <TableCell>{formatPrice(signal.target)}</TableCell>
              <TableCell>{formatPrice(signal.stop)}</TableCell>
              <TableCell>{signal.score ?? '—'}</TableCell>
              <TableCell>{signal.rank ?? '—'}</TableCell>
            </TableRow>
          ))}

          {!isLoading && signals.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} align="center">
                <Typography variant="body2" color="text.secondary">
                  Nenhum sinal encontrado para o período informado.
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </Paper>
  )
}

export default SignalsHistoryTable
