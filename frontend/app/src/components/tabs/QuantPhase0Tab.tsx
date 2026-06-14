import {
  Alert,
  Chip,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { QuantDataInventorySummary, QuantDataQualityIncident, QuantTickerCoverage } from '../../api/ops'

interface QuantPhase0TabProps {
  summary?: QuantDataInventorySummary | null
  summaryError?: Error | null
  summaryLoading: boolean
  coverage: QuantTickerCoverage[]
  coverageError?: Error | null
  coverageLoading: boolean
  incidents: QuantDataQualityIncident[]
  incidentsError?: Error | null
  incidentsLoading: boolean
}

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('pt-BR').format(value) : '—'

const formatCurrency = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value)
    : '—'

const formatPct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : '—'

const formatDate = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const statusColor = (status: string) => {
  const normalized = status.toLowerCase()
  if (normalized === 'elegivel') return 'success'
  if (normalized === 'observacao') return 'warning'
  if (normalized === 'inativo') return 'default'
  return 'error'
}

const SummaryCard: FC<{ title: string; value: string; helper?: string }> = ({ title, value, helper }) => (
  <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, flex: 1, minWidth: 220 }}>
    <Stack spacing={0.75}>
      <Typography variant="overline" color="text.secondary">{title}</Typography>
      <Typography variant="h5" fontWeight={800}>{value}</Typography>
      {helper ? <Typography variant="caption" color="text.secondary">{helper}</Typography> : null}
    </Stack>
  </Paper>
)

const QuantPhase0Tab: FC<QuantPhase0TabProps> = ({
  summary,
  summaryError,
  summaryLoading,
  coverage,
  coverageError,
  coverageLoading,
  incidents,
  incidentsError,
  incidentsLoading,
}) => {
  const eligibleCount = coverage.filter((item) => item.eligibilityStatus.toLowerCase() === 'elegivel').length
  const observationCount = coverage.filter((item) => item.eligibilityStatus.toLowerCase() === 'observacao').length

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">Fase 0 — Inventário Quantitativo</Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhe as views de inventário e qualidade criadas para validar a base antes dos novos sistemas quantitativos.
        </Typography>
      </Stack>

      {summaryLoading ? <Skeleton variant="rounded" height={150} /> : null}
      {summaryError ? <Alert severity="error">Erro ao carregar o resumo do inventário quantitativo.</Alert> : null}
      {!summaryLoading && !summaryError && !summary ? <Alert severity="info">Ainda não há resumo de inventário disponível.</Alert> : null}
      {summary ? (
        <Stack direction="row" flexWrap="wrap" gap={2}>
          <SummaryCard title="Tickers ativos" value={formatNumber(summary.activeTickers)} helper={`${formatNumber(summary.totalTickers)} tickers cadastrados`} />
          <SummaryCard title="Período histórico" value={`${formatDate(summary.firstAvailableDate)} — ${formatDate(summary.lastAvailableDate)}`} />
          <SummaryCard title="Candles diários" value={formatNumber(summary.dailyCandles)} helper={`${formatNumber(summary.dailyTickers)} tickers cobertos`} />
          <SummaryCard title="Candles intraday" value={formatNumber(summary.intradayCandles)} helper={`${formatNumber(summary.intradayTickers)} tickers cobertos`} />
          <SummaryCard title="Dados válidos" value={formatPct(summary.validDataPct)} helper={`Atualizado em ${formatDateTime(summary.lastUpdate)}`} />
          <SummaryCard title="Universo inicial" value={`${eligibleCount} elegíveis`} helper={`${observationCount} em observação na amostra carregada`} />
        </Stack>
      ) : null}

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h5" fontWeight={700}>Inventário de Dados — cobertura por ticker</Typography>
          {coverageError ? <Alert severity="error">Erro ao carregar cobertura por ticker.</Alert> : null}
          {coverageLoading ? <Skeleton variant="rounded" height={280} /> : null}
          {!coverageLoading && !coverageError ? (
            <TableContainer sx={{ maxHeight: 460 }}>
              <Table stickyHeader size="small" aria-label="Cobertura por ticker">
                <TableHead>
                  <TableRow>
                    <TableCell>Ticker</TableCell>
                    <TableCell>Empresa</TableCell>
                    <TableCell>Período</TableCell>
                    <TableCell align="right">Cobertura</TableCell>
                    <TableCell align="right">Dias</TableCell>
                    <TableCell align="right">Volume médio</TableCell>
                    <TableCell align="right">Inválidos</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {coverage.map((item) => (
                    <TableRow key={item.ticker} hover>
                      <TableCell><Typography fontWeight={700}>{item.ticker}</Typography></TableCell>
                      <TableCell>{item.company ?? '—'}</TableCell>
                      <TableCell>{formatDate(item.firstDate)} — {formatDate(item.lastDate)}</TableCell>
                      <TableCell align="right">{formatPct(item.coveragePct)}</TableCell>
                      <TableCell align="right">{formatNumber(item.daysWithData)} / {formatNumber(item.expectedDays)}</TableCell>
                      <TableCell align="right">{formatCurrency(item.avgFinancialVolume)}</TableCell>
                      <TableCell align="right">{formatNumber(item.invalidPriceDays + item.invalidVolumeDays + item.duplicateDays)}</TableCell>
                      <TableCell><Chip size="small" label={item.eligibilityStatus} color={statusColor(item.eligibilityStatus)} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </Stack>
      </Paper>

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h5" fontWeight={700}>Qualidade dos Dados — incidentes derivados</Typography>
          {incidentsError ? <Alert severity="error">Erro ao carregar incidentes quantitativos.</Alert> : null}
          {incidentsLoading ? <Skeleton variant="rounded" height={220} /> : null}
          {!incidentsLoading && !incidentsError && incidents.length === 0 ? <Alert severity="success">Nenhum incidente derivado encontrado nas views da Fase 0.</Alert> : null}
          {!incidentsLoading && !incidentsError && incidents.length > 0 ? (
            <TableContainer sx={{ maxHeight: 360 }}>
              <Table stickyHeader size="small" aria-label="Incidentes quantitativos">
                <TableHead>
                  <TableRow>
                    <TableCell>Data</TableCell>
                    <TableCell>Ticker</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell>Severidade</TableCell>
                    <TableCell>Recomendação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {incidents.map((incident, index) => (
                    <TableRow key={`${incident.ticker}-${incident.incidentType}-${incident.incidentDate}-${index}`} hover>
                      <TableCell>{formatDate(incident.incidentDate)}</TableCell>
                      <TableCell><Typography fontWeight={700}>{incident.ticker}</Typography></TableCell>
                      <TableCell>{incident.incidentType}</TableCell>
                      <TableCell><Chip size="small" label={incident.severity} color={incident.severity === 'high' ? 'error' : 'warning'} /></TableCell>
                      <TableCell>{incident.recommendation ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  )
}

export default QuantPhase0Tab
