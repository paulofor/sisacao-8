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
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  LinearProgress,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { NeuralTrainingRun } from '../../api/ops'

interface NeuralTrainingRunsTabProps {
  runs: NeuralTrainingRun[]
  runsError?: Error | null
  runsLoading: boolean
}


interface NeuralSplitMetrics {
  rowsCount: number | null
  accuracy: number | null
  directionalPrecision: number | null
  coverage: number | null
}

const asNumber = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

const parseMetricsJson = (value: string | null | undefined): Record<string, unknown> => {
  if (!value) return {}
  try {
    const parsed = JSON.parse(value) as unknown
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {}
  } catch {
    return {}
  }
}

const splitMetrics = (
  run: NeuralTrainingRun,
  split: 'train' | 'validation' | 'test',
): NeuralSplitMetrics => {
  const metrics = parseMetricsJson(run.metricsJson)
  const splitValue = metrics[split]
  const splitRecord =
    splitValue && typeof splitValue === 'object' && !Array.isArray(splitValue)
      ? (splitValue as Record<string, unknown>)
      : {}

  return {
    rowsCount: asNumber(splitRecord.rows_count ?? splitRecord.rowsCount),
    accuracy:
      asNumber(splitRecord.accuracy) ??
      (split === 'validation' ? run.validationAccuracy : split === 'test' ? run.testAccuracy : null),
    directionalPrecision:
      asNumber(splitRecord.directional_precision ?? splitRecord.directionalPrecision) ??
      (split === 'test' ? run.directionalPrecision : null),
    coverage: asNumber(splitRecord.coverage) ?? (split === 'test' ? run.coverage : null),
  }
}

const latestTestMetrics = (runs: NeuralTrainingRun[]) =>
  latestRun(runs) ? splitMetrics(latestRun(runs), 'test') : null

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR').format(value)
    : '—'

const formatPct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value)
    : '—'

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const statusColor = (status: string | null) => {
  const normalized = status?.toLowerCase()
  if (normalized === 'approved') return 'success'
  if (normalized === 'paper' || normalized === 'shadow') return 'info'
  if (normalized === 'candidate') return 'warning'
  if (normalized === 'rejected') return 'error'
  return 'default'
}

const statusLabel = (status: string | null) => {
  if (!status) return 'Sem status'
  const normalized = status.toLowerCase()
  if (normalized === 'candidate') return 'Candidato'
  if (normalized === 'shadow') return 'Shadow'
  if (normalized === 'paper') return 'Paper'
  if (normalized === 'approved') return 'Aprovado'
  if (normalized === 'rejected') return 'Rejeitado'
  return status
}

const latestRun = (runs: NeuralTrainingRun[]) => runs[0]

const bestTestAccuracy = (runs: NeuralTrainingRun[]) => {
  const values = runs
    .map((run) => run.testAccuracy)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
  return values.length > 0 ? Math.max(...values) : null
}

const SummaryCard: FC<{ title: string; value: string; helper?: string }> = ({
  title,
  value,
  helper,
}) => (
  <Paper
    elevation={0}
    sx={{
      p: 2.5,
      border: '1px solid',
      borderColor: 'divider',
      borderRadius: 2,
      flex: 1,
      minWidth: 220,
    }}
  >
    <Stack spacing={0.75}>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
      <Typography variant="h5" fontWeight={800}>
        {value}
      </Typography>
      {helper ? (
        <Typography variant="caption" color="text.secondary">
          {helper}
        </Typography>
      ) : null}
    </Stack>
  </Paper>
)

const NeuralTrainingRunsTab: FC<NeuralTrainingRunsTabProps> = ({
  runs,
  runsError,
  runsLoading,
}) => {
  const latest = latestRun(runs)
  const approvedCount = runs.filter(
    (run) => run.status?.toLowerCase() === 'approved',
  ).length
  const latestTest = latestTestMetrics(runs)

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Redes neurais — Treinos
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhe os artefatos treinados, versões, status de governança,
          métricas de validação/teste e localização do modelo salvo.
        </Typography>
      </Stack>

      {runsLoading ? <Skeleton variant="rounded" height={150} /> : null}
      {runsError ? (
        <Alert severity="error">Erro ao carregar os treinos neurais.</Alert>
      ) : null}
      {!runsLoading && !runsError && runs.length === 0 ? (
        <Alert severity="info">
          Ainda não há treinos neurais registrados para acompanhamento.
        </Alert>
      ) : null}

      {runs.length > 0 ? (
        <>
          <Stack direction="row" flexWrap="wrap" gap={2}>
            <SummaryCard
              title="Treinos registrados"
              value={formatNumber(runs.length)}
              helper={`${formatNumber(approvedCount)} aprovados para uso controlado`}
            />
            <SummaryCard
              title="Último treino"
              value={formatDateTime(latest?.trainedAt)}
              helper={latest?.modelVersion ?? '—'}
            />
            <SummaryCard
              title="Melhor acurácia teste"
              value={formatPct(bestTestAccuracy(runs))}
              helper="Entre os artefatos registrados"
            />
            <SummaryCard
              title="Última precisão direcional"
              value={formatPct(latest?.directionalPrecision)}
              helper={`Cobertura: ${formatPct(latest?.coverage)}`}
            />
          </Stack>

          <Paper
            elevation={0}
            sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
          >
            <Stack spacing={1.5}>
              <Typography variant="h6" fontWeight={800}>
                Performance da rede mais recente no split de teste
              </Typography>
              <Stack direction="row" flexWrap="wrap" gap={2}>
                <SummaryCard title="Acurácia teste" value={formatPct(latestTest?.accuracy)} />
                <SummaryCard
                  title="Precisão direcional"
                  value={formatPct(latestTest?.directionalPrecision)}
                />
                <SummaryCard title="Cobertura direcional" value={formatPct(latestTest?.coverage)} />
                <SummaryCard title="Amostras testadas" value={formatNumber(latestTest?.rowsCount)} />
              </Stack>
              {typeof latestTest?.accuracy === 'number' ? (
                <LinearProgress
                  variant="determinate"
                  value={Math.max(0, Math.min(100, latestTest.accuracy * 100))}
                  sx={{ height: 10, borderRadius: 999 }}
                />
              ) : null}
              <Typography variant="caption" color="text.secondary">
                Métricas extraídas do registro auditável do treino (`metrics_json`), com fallback para
                os campos consolidados quando o detalhe por split não estiver presente.
              </Typography>
            </Stack>
          </Paper>

          <TableContainer
            component={Paper}
            elevation={0}
            sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
          >
            <Table stickyHeader size="small" aria-label="Treinos neurais registrados">
              <TableHead>
                <TableRow>
                  <TableCell>Modelo</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Treinado em</TableCell>
                  <TableCell align="right">Validação</TableCell>
                  <TableCell align="right">Teste</TableCell>
                  <TableCell align="right">Linhas teste</TableCell>
                  <TableCell align="right">Precisão dir.</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell>Contrato</TableCell>
                  <TableCell>Artefato</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={`${run.modelId}-${run.modelVersion}`} hover>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2" fontWeight={700}>
                          {run.modelId || '—'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {run.modelVersion || '—'}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={statusLabel(run.status)}
                        color={statusColor(run.status)}
                      />
                    </TableCell>
                    <TableCell>{formatDateTime(run.trainedAt)}</TableCell>
                    <TableCell align="right">{formatPct(run.validationAccuracy)}</TableCell>
                    <TableCell align="right">{formatPct(run.testAccuracy)}</TableCell>
                    <TableCell align="right">{formatNumber(splitMetrics(run, 'test').rowsCount)}</TableCell>
                    <TableCell align="right">{formatPct(run.directionalPrecision)}</TableCell>
                    <TableCell align="right">{formatPct(run.coverage)}</TableCell>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="caption">
                          Features: {run.featureVersion || '—'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Labels: {run.labelVersion || '—'} ·{' '}
                          {formatNumber(run.featureColumnsCount)} colunas
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Box
                        component="span"
                        sx={{
                          display: 'inline-block',
                          maxWidth: 260,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          verticalAlign: 'bottom',
                        }}
                        title={run.artifactUri ?? undefined}
                      >
                        {run.artifactUri || '—'}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : null}
    </Stack>
  )
}

export default NeuralTrainingRunsTab
