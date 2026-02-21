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

import type { OpsSignalNext } from '../../api/ops'
import StatusChip from '../StatusChip'

interface SignalsNextTableProps {
  signals: OpsSignalNext[]
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

const formatScore = (value: number | null) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toFixed(2)
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

const SignalsNextTable: FC<SignalsNextTableProps> = ({ signals, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Não foi possível carregar os sinais do próximo pregão.</Alert>
  }

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <Typography variant="h6" fontWeight={600} sx={{ p: 3, pb: 0 }}>
        Top 5 – Próximo Pregão
      </Typography>
      <Table size="small" aria-label="Sinais do próximo pregão">
        <TableHead>
          <TableRow>
            <TableCell>Ticker</TableCell>
            <TableCell>Side</TableCell>
            <TableCell>Entry</TableCell>
            <TableCell>Target</TableCell>
            <TableCell>Stop</TableCell>
            <TableCell>Score</TableCell>
            <TableCell>Rank</TableCell>
            <TableCell>Válido para</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading && signals.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} align="center">
                <Typography variant="body2" color="text.secondary">
                  Carregando sinais...
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}

          {signals.map((signal) => (
            <TableRow key={`${signal.ticker}-${signal.rank}`} hover>
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
              <TableCell>{formatScore(signal.score)}</TableCell>
              <TableCell>{signal.rank ?? '—'}</TableCell>
              <TableCell>{formatDate(signal.validFor)}</TableCell>
            </TableRow>
          ))}

          {!isLoading && signals.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} align="center">
                <Typography variant="body2" color="text.secondary">
                  Nenhum sinal disponível para o próximo pregão.
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </Paper>
  )
}

export default SignalsNextTable
