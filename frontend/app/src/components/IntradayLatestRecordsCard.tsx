import type { FC } from 'react'

import {
  Alert,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'

import type { IntradayLatestRecord } from '../api/dataCollections'

interface IntradayLatestRecordsCardProps {
  records?: IntradayLatestRecord[]
  isLoading: boolean
  error: Error | null
}

const formatPrice = (price?: number | null): string => {
  if (typeof price !== 'number' || Number.isNaN(price)) {
    return '—'
  }

  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  }).format(price)
}

const formatCapturedAt = (record: IntradayLatestRecord): string => {
  if (record.capturedAt) {
    const rawCapturedAt = record.capturedAt.trim()
    const isoWithoutTimezone = rawCapturedAt.match(
      /^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/,
    )

    if (isoWithoutTimezone) {
      const [, year, month, day, hour, minute, second] = isoWithoutTimezone
      return `${day}/${month}/${year} ${hour}:${minute}:${second}`
    }

    const parsed = dayjs(rawCapturedAt)
    if (parsed.isValid()) {
      return parsed.format('DD/MM/YYYY HH:mm:ss')
    }

    return rawCapturedAt
  }

  const date = record.tradeDate?.trim()
  const time = record.tradeTime?.trim()
  if (date) {
    return time ? `${date} ${time}` : date
  }

  return '—'
}

const IntradayLatestRecordsCard: FC<IntradayLatestRecordsCardProps> = ({ records, isLoading, error }) => {
  if (isLoading) {
    return (
      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
        <Stack spacing={2}>
          <Skeleton variant="text" width={300} height={36} />
          <Skeleton variant="rectangular" height={170} />
        </Stack>
      </Paper>
    )
  }

  if (error) {
    return <Alert severity="error">Não foi possível carregar os últimos registros intraday da tabela cotacao_b3.</Alert>
  }

  const latestRecords = records ?? []

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h5" color="text.primary" fontWeight={700}>
          Últimos registros intraday (cotacao_b3)
        </Typography>

        {latestRecords.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Ainda não há registros para exibir.
          </Typography>
        ) : (
          <Table size="small" aria-label="Últimos registros intraday">
            <TableHead>
              <TableRow>
                <TableCell>Ticker</TableCell>
                <TableCell>Preço</TableCell>
                <TableCell>Data/hora de captura</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {latestRecords.map((record, index) => (
                <TableRow key={`${record.ticker}-${record.capturedAt ?? record.tradeDate ?? index}`} hover>
                  <TableCell>{record.ticker || '—'}</TableCell>
                  <TableCell>{formatPrice(record.price)}</TableCell>
                  <TableCell>{formatCapturedAt(record)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Stack>
    </Paper>
  )
}

export default IntradayLatestRecordsCard
