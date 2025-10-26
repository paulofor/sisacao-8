import {
  Alert,
  Box,
  Chip,
  Divider,
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

import type { IntradaySummary } from '../api/dataCollections'

interface IntradaySummaryCardProps {
  summary?: IntradaySummary
  isLoading: boolean
  error?: Error | null
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
})

const formatPrice = (price?: number | null) => {
  if (typeof price === 'number' && Number.isFinite(price)) {
    return currencyFormatter.format(price)
  }
  return '—'
}

const formatStatusLabel = (success: boolean, error?: string | null) => {
  if (success) {
    return 'Sucesso'
  }
  if (error) {
    return 'Falha'
  }
  return 'Sem dados'
}

const formatStatusColor = (success: boolean, error?: string | null) => {
  if (success) {
    return 'success'
  }
  if (error) {
    return 'error'
  }
  return 'default'
}

const StatItem: FC<{ label: string; value: string | number }> = ({ label, value }) => (
  <Stack spacing={0.5}>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
    <Typography variant="h5" color="text.primary" fontWeight={700}>
      {value}
    </Typography>
  </Stack>
)

const IntradaySummaryCard: FC<IntradaySummaryCardProps> = ({ summary, isLoading, error }) => {
  if (isLoading) {
    return (
      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
        <Stack spacing={2}>
          <Skeleton variant="text" width={240} height={36} />
          <Skeleton variant="rectangular" height={80} />
          <Skeleton variant="rectangular" height={140} />
        </Stack>
      </Paper>
    )
  }

  if (error) {
    return (
      <Alert severity="error">
        Não foi possível carregar o resumo intraday. Verifique a API do backend e tente novamente.
      </Alert>
    )
  }

  const tickers = summary?.tickers ?? []
  const hasData = tickers.length > 0
  const updatedLabel = summary?.updatedAt
    ? `Última atualização às ${dayjs(summary.updatedAt).format('DD/MM/YYYY HH:mm:ss')}`
    : 'Sem registros recentes'
  const totalTickers = summary?.totalTickers ?? 0
  const successfulTickers = summary?.successfulTickers ?? 0
  const failedTickers = summary?.failedTickers ?? 0

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 3 }}>
      <Stack spacing={3}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', md: 'center' }}>
          <Typography variant="h5" color="text.primary" fontWeight={700}>
            Resumo das Coletas Intraday
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ ml: { md: 'auto' } }}>
            {updatedLabel}
          </Typography>
        </Stack>

        {hasData ? (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <StatItem label="Tickers monitorados" value={totalTickers} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <StatItem label="Capturas com sucesso" value={successfulTickers} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <StatItem label="Falhas registradas" value={failedTickers} />
            </Box>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Ainda não existem registros de coletas intraday disponíveis para exibição.
          </Typography>
        )}

        {hasData ? (
          <>
            <Divider />
            <Table size="small" aria-label="Resumo de tickers intraday">
              <TableHead>
                <TableRow>
                  <TableCell width="25%">Ticker</TableCell>
                  <TableCell width="25%">Preço coletado</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tickers.map((ticker) => {
                  const statusLabel = formatStatusLabel(ticker.success, ticker.error)
                  const statusColor = formatStatusColor(ticker.success, ticker.error)
                  return (
                    <TableRow key={ticker.ticker} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600} color="text.primary">
                          {ticker.ticker}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.primary">
                          {formatPrice(ticker.price)}
                        </Typography>
                        {ticker.error ? (
                          <Typography variant="caption" color="text.secondary">
                            {ticker.error}
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <Chip label={statusLabel} color={statusColor} size="small" sx={{ fontWeight: 600 }} />
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </>
        ) : null}
      </Stack>
    </Paper>
  )
}

export default IntradaySummaryCard
