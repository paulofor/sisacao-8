import { Alert, Paper, Skeleton, Stack, Typography } from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { OpsOverview } from '../../api/ops'
import StatusChip from '../StatusChip'

interface OpsOverviewCardsProps {
  overview?: OpsOverview | null
  isLoading: boolean
  error?: Error | null
}

const formatDateTime = (value: string | null) => {
  if (!value) {
    return '—'
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const formatDate = (value: string | null) => {
  if (!value) {
    return '—'
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

interface OverviewCardProps {
  title: string
  status?: string | null
  helper?: string
}

const OverviewCard: FC<OverviewCardProps> = ({ title, status, helper }) => {
  return (
    <Paper
      elevation={0}
      sx={{
        flex: 1,
        p: 2.5,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        minWidth: { xs: '100%', md: 0 },
      }}
    >
      <Stack spacing={1}>
        <Typography variant="overline" color="text.secondary">
          {title}
        </Typography>
        <StatusChip status={status} size="medium" />
        {helper ? (
          <Typography variant="caption" color="text.secondary">
            {helper}
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  )
}

const OpsOverviewCards: FC<OpsOverviewCardsProps> = ({ overview, isLoading, error }) => {
  if (isLoading) {
    return (
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <Skeleton variant="rounded" height={160} sx={{ flex: 1 }} />
        <Skeleton variant="rounded" height={160} sx={{ flex: 1 }} />
        <Skeleton variant="rounded" height={160} sx={{ flex: 1 }} />
      </Stack>
    )
  }

  if (error) {
    return (
      <Alert severity="error">Não foi possível carregar a visão geral da operação. Verifique o backend e tente novamente.</Alert>
    )
  }

  if (!overview) {
    return <Alert severity="info">Ainda não há dados operacionais disponíveis para exibição.</Alert>
  }

  const asOfLabel = overview.asOf ? `Consolidado às ${formatDateTime(overview.asOf)}` : 'Sem horário consolidado'
  const signalsHelper = overview.lastSignalsGeneratedAt
    ? `Últimos sinais gerados às ${formatDateTime(overview.lastSignalsGeneratedAt)}`
    : 'Sem geração recente'

  return (
    <Stack spacing={2.5}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'flex-start', md: 'center' }}>
        <Typography variant="h5" fontWeight={700} color="text.primary">
          Visão Geral da Operação
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ ml: { md: 'auto' } }}>
          {asOfLabel}
        </Typography>
      </Stack>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <OverviewCard title="Pipeline" status={overview.pipelineHealth ?? '—'} helper={`Próximo pregão: ${formatDate(overview.nextTradingDay)}`} />
        <OverviewCard title="Data Quality" status={overview.dqHealth ?? '—'} helper={`Último DQ: ${formatDate(overview.lastTradingDay)}`} />
        <OverviewCard
          title="Sinais"
          status={overview.signalsReady ? 'READY' : 'PENDING'}
          helper={`${overview.signalsCount} produtos prontos · ${signalsHelper}`}
        />
      </Stack>
    </Stack>
  )
}

export default OpsOverviewCards
