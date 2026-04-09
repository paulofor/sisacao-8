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
const DISPLAY_DAYS = 5

const COMPARISON_WINDOWS = [5, 10] as const

type TableStatus = 'OK' | 'WARN' | 'ERRO'

const statusColor: Record<TableStatus, 'success' | 'warning' | 'error'> = {
  OK: 'success',
  WARN: 'warning',
  ERRO: 'error',
}

const formatComparisonLabel = (difference: number, percentage: number | null): string => {
  const signedDifference = `${difference > 0 ? '+' : ''}${difference.toLocaleString('pt-BR')}`
  if (percentage === null) {
    return signedDifference
  }

  return `${signedDifference} (${percentage > 0 ? '+' : ''}${percentage.toFixed(1)}%)`
}

const comparisonColor = (difference: number): 'success' | 'warning' | 'default' => {
  if (difference > 0) {
    return 'success'
  }

  if (difference < 0) {
    return 'warning'
  }

  return 'default'
}

const CandlesTableHealthCard: FC<CandlesTableHealthCardProps> = ({ counts, isLoading, error }) => {
  const allDates = Array.from(new Set((counts ?? []).map((item) => item.date))).sort((a, b) => dayjs(b).valueOf() - dayjs(a).valueOf())

  const availableDates = allDates.slice(0, DISPLAY_DAYS)

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

    const comparisons = COMPARISON_WINDOWS.map((windowDays) => {
      if (!latest || tableRecords.length <= windowDays) {
        return {
          windowDays,
          date: null,
          difference: null,
          percentage: null,
        }
      }

      const reference = tableRecords[windowDays]
      const difference = latest.totalRecords - reference.totalRecords
      const percentage = reference.totalRecords > 0 ? (difference / reference.totalRecords) * 100 : null

      return {
        windowDays,
        date: reference.date,
        difference,
        percentage,
      }
    })

    let status: TableStatus = 'ERRO'
    if (latest) {
      status = latest.totalRecords > 0 ? 'OK' : 'WARN'
    }

    return {
      tableName,
      comparisons,
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
                  <TableCell align="right">Comparação (5 dias)</TableCell>
                  <TableCell align="right">Comparação (10 dias)</TableCell>
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
                    {row.comparisons.map((comparison) => (
                      <TableCell key={`${row.tableName}-comparison-${comparison.windowDays}`} align="right">
                        {comparison.difference === null ? (
                          '—'
                        ) : (
                          <Tooltip
                            title={`Base ${comparison.windowDays} dias (${dayjs(comparison.date).format('DD/MM/YYYY')}): ${formatComparisonLabel(
                              comparison.difference,
                              comparison.percentage,
                            )}`}
                          >
                            <Chip
                              label={formatComparisonLabel(comparison.difference, comparison.percentage)}
                              color={comparisonColor(comparison.difference)}
                              size="small"
                              variant="outlined"
                            />
                          </Tooltip>
                        )}
                      </TableCell>
                    ))}
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
