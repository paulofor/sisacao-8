import {
  Alert,
  Box,
  Chip,
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
import type { FC } from 'react'

import type { IntradayDailyCount } from '../api/dataCollections'

interface IntradayDailyCountsCardProps {
  counts?: IntradayDailyCount[]
  isLoading: boolean
  error?: Error | null
}

const IntradayDailyCountsCard: FC<IntradayDailyCountsCardProps> = ({ counts, isLoading, error }) => {
  if (isLoading) {
    return (
      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
        <Stack spacing={2}>
          <Skeleton variant="text" width={260} height={36} />
          <Skeleton variant="rectangular" height={96} />
          <Skeleton variant="rectangular" height={120} />
        </Stack>
      </Paper>
    )
  }

  if (error) {
    return <Alert severity="error">Não foi possível carregar o volume diário de registros.</Alert>
  }

  const items = counts ?? []
  const totalInWindow = items.reduce((acc, item) => acc + item.totalRecords, 0)

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
      <Stack spacing={3}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', md: 'center' }}>
          <Typography variant="h5" color="text.primary" fontWeight={700}>
            Volume diário de inserções (Intraday)
          </Typography>
          <Chip
            label={`${totalInWindow.toLocaleString('pt-BR')} registros nos últimos ${items.length} dias`}
            color="primary"
            variant="outlined"
            size="small"
            sx={{ ml: { md: 'auto' }, fontWeight: 600 }}
          />
        </Stack>

        {items.length > 0 ? (
          <Table size="small" aria-label="Contagem diária de registros intraday">
            <TableHead>
              <TableRow>
                <TableCell width="50%">Data</TableCell>
                <TableCell align="right">Quantidade de registros</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.date} hover>
                  <TableCell>
                    <Typography variant="body2" color="text.primary" fontWeight={600}>
                      {dayjs(item.date).format('DD/MM/YYYY')}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.primary" fontWeight={600}>
                      {item.totalRecords.toLocaleString('pt-BR')}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Box>
            <Typography variant="body2" color="text.secondary">
              Nenhum registro encontrado para os últimos dias na tabela de intraday.
            </Typography>
          </Box>
        )}
      </Stack>
    </Paper>
  )
}

export default IntradayDailyCountsCard
