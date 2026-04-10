import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { CandlesTableDailyCount } from '../api/dataCollections'

interface CandlesTableHealthCardProps {
  counts?: CandlesTableDailyCount[]
  isLoading: boolean
  error?: Error | null
}

const TARGET_TABLES = ['candles_diarios', 'candles_intraday_15m', 'candles_intraday_1h'] as const
const DISPLAY_DAYS = 10

type TableStatus = 'OK' | 'WARN' | 'ERRO'

const statusColor: Record<TableStatus, 'success' | 'warning' | 'error'> = {
  OK: 'success',
  WARN: 'warning',
  ERRO: 'error',
}

const CandlesTableHealthCard: FC<CandlesTableHealthCardProps> = ({ counts, isLoading, error }) => {
  const mostRecentDate = (counts ?? [])
    .map((item) => dayjs(item.date))
    .sort((a, b) => b.valueOf() - a.valueOf())[0] ?? dayjs()
  const availableDates = Array.from({ length: DISPLAY_DAYS }, (_, index) =>
    mostRecentDate.subtract(index, 'day').format('YYYY-MM-DD'),
  )

  const rows = TARGET_TABLES.map((tableName) => {
    const tableRecords = (counts ?? [])
      .filter((item) => item.tableName === tableName)
      .sort((a, b) => dayjs(b.date).valueOf() - dayjs(a.date).valueOf())

    const latest = tableRecords[0]
    const byDate = new Map(tableRecords.map((item) => [item.date, item.totalRecords]))

    const dailyTotals = availableDates.map((date) => ({
      date,
      total: byDate.get(date) ?? 0,
    }))

    let status: TableStatus = 'ERRO'
    if (latest) {
      status = latest.totalRecords > 0 ? 'OK' : 'WARN'
    }

    return {
      tableName,
      dailyTotals,
      status,
    }
  })

  return (
    <Card>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h6">Saúde de população das tabelas de candles</Typography>
          <Typography variant="body2" color="text.secondary">
            Acompanhamento das tabelas <code>candles_diarios</code>, <code>candles_intraday_15m</code> e{' '}
            <code>candles_intraday_1h</code> para validar se o volume está sendo carregado.
          </Typography>

          {error ? <Alert severity="error">Não foi possível carregar os indicadores de população das tabelas de candles.</Alert> : null}

          {isLoading ? (
            <Stack spacing={1}>
              <Skeleton variant="rounded" height={36} />
              <Skeleton variant="rounded" height={36} />
              <Skeleton variant="rounded" height={36} />
            </Stack>
          ) : (
            <Table size="small" aria-label="Saúde das tabelas de candles">
              <TableHead>
                <TableRow>
                  <TableCell>Tabela</TableCell>
                  {availableDates.map((date) => (
                    <TableCell key={date} align="right">
                      {dayjs(date).format('DD/MM')}
                    </TableCell>
                  ))}
                  <TableCell align="right">Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.tableName}>
                    <TableCell>{row.tableName}</TableCell>
                    {row.dailyTotals.map((entry) => (
                      <TableCell key={`${row.tableName}-${entry.date}`} align="right">
                        <Tooltip title={`${dayjs(entry.date).format('DD/MM/YYYY')}: ${entry.total.toLocaleString('pt-BR')} registros`}>
                          <Box component="span" sx={{ fontWeight: 600, color: entry.total === 0 ? 'text.disabled' : 'text.primary' }}>
                            {entry.total.toLocaleString('pt-BR')}
                          </Box>
                        </Tooltip>
                      </TableCell>
                    ))}
                    <TableCell align="right">
                      <Chip label={row.status} color={statusColor[row.status]} size="small" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}

export default CandlesTableHealthCard
