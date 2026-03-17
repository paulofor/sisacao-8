import { Alert, Card, CardContent, Chip, Skeleton, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { CandlesTableDailyCount } from '../api/dataCollections'

interface CandlesTableHealthCardProps {
  counts?: CandlesTableDailyCount[]
  isLoading: boolean
  error?: Error | null
}

const TARGET_TABLES = ['candles_diarios', 'candles_intraday_15m', 'candles_intraday_1h'] as const

type TableStatus = 'OK' | 'WARN' | 'ERRO'

const statusColor: Record<TableStatus, 'success' | 'warning' | 'error'> = {
  OK: 'success',
  WARN: 'warning',
  ERRO: 'error',
}

const CandlesTableHealthCard: FC<CandlesTableHealthCardProps> = ({ counts, isLoading, error }) => {
  const today = dayjs().format('YYYY-MM-DD')

  const rows = TARGET_TABLES.map((tableName) => {
    const tableRecords = (counts ?? []).filter((item) => item.tableName === tableName)
    const latest = tableRecords[0]
    const todayTotal = tableRecords.find((item) => item.date === today)?.totalRecords ?? 0

    let status: TableStatus = 'ERRO'
    if (latest) {
      status = latest.totalRecords > 0 ? 'OK' : 'WARN'
    }

    return {
      tableName,
      latestDate: latest?.date ?? '—',
      latestTotal: latest?.totalRecords ?? 0,
      todayTotal,
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
                  <TableCell>Última data</TableCell>
                  <TableCell align="right">Registros na última data</TableCell>
                  <TableCell align="right">Registros hoje</TableCell>
                  <TableCell align="right">Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.tableName}>
                    <TableCell>{row.tableName}</TableCell>
                    <TableCell>{row.latestDate}</TableCell>
                    <TableCell align="right">{row.latestTotal}</TableCell>
                    <TableCell align="right">{row.todayTotal}</TableCell>
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
