import {
  Alert,
  Box,
  Chip,
  LinearProgress,
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

import type { NeuralGateDecisionAttempt, NeuralTrainingRun } from '../../api/ops'

interface NeuralTrainingRunsTabProps {
  runs: NeuralTrainingRun[]
  runsError?: Error | null
  runsLoading: boolean
  gateDecisions?: NeuralGateDecisionAttempt[]
  gateDecisionsError?: Error | null
  gateDecisionsLoading?: boolean
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

const latestTrainMetrics = (runs: NeuralTrainingRun[]) =>
  latestRun(runs) ? splitMetrics(latestRun(runs), 'train') : null

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


const gateStatusColor = (attempt: NeuralGateDecisionAttempt) => {
  const normalized = attempt.decisionStatus?.toLowerCase()
  if (attempt.passed || normalized === 'passed') return 'success'
  if (normalized === 'rejected') return 'error'
  return 'default'
}

const gateStatusLabel = (attempt: NeuralGateDecisionAttempt) => {
  const normalized = attempt.decisionStatus?.toLowerCase()
  if (attempt.passed || normalized === 'passed') return 'Aprovado'
  if (normalized === 'rejected') return 'Rejeitado'
  if (normalized === 'blocked') return 'Bloqueado'
  return attempt.decisionStatus ?? 'Sem decisão'
}

const formatCriteria = (value: string | null | undefined) => {
  if (!value) return '—'
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .join(' · ') || '—'
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
  gateDecisions = [],
  gateDecisionsError,
  gateDecisionsLoading = false,
}) => {
  const latest = latestRun(runs)
  const approvedCount = runs.filter(
    (run) => run.status?.toLowerCase() === 'approved',
  ).length
  const candidateCount = runs.filter((run) => run.status?.toLowerCase() === 'candidate').length
  const activeTrainingCount = runs.filter((run) => ['running', 'training', 'in_progress'].includes(run.status?.toLowerCase() ?? '')).length
  const rejectedCount = runs.filter((run) => ['rejected', 'reject'].includes(run.status?.toLowerCase() ?? '')).length
  const rejectedGateDecisions = gateDecisions.filter((attempt) => attempt.decisionStatus?.toLowerCase() === 'rejected' || attempt.passed === false)
  const passedGateDecisions = gateDecisions.filter((attempt) => attempt.passed || attempt.decisionStatus?.toLowerCase() === 'passed')
  const latestGateDecisions = gateDecisions.slice(0, 8)
  const latestTrain = latestTrainMetrics(runs)
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
              title="Total de redes"
              value={formatNumber(runs.length)}
              helper="artefatos treinados/registrados"
            />
            <SummaryCard
              title="Em treino agora"
              value={formatNumber(activeTrainingCount)}
              helper="status running/training/in_progress"
            />
            <SummaryCard
              title="Candidatas"
              value={formatNumber(candidateCount)}
              helper="prontas para avaliação/evolução"
            />
            <SummaryCard
              title="Aprovadas"
              value={formatNumber(approvedCount)}
              helper={`${formatNumber(rejectedCount)} rejeitadas no registro`}
            />
            <SummaryCard
              title="Rejeitadas no gate"
              value={formatNumber(rejectedGateDecisions.length)}
              helper={`${formatNumber(gateDecisions.length)} decisões MUEN; ${formatNumber(passedGateDecisions.length)} aprovadas`}
            />
          </Stack>

          <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <Typography variant="h6" fontWeight={800}>Como ler o estágio de cada rede</Typography>
              <Stack direction="row" flexWrap="wrap" gap={1.5}>
                {[
                  { label: 'Em treino', value: activeTrainingCount, color: 'info' as const, helper: 'ainda executando' },
                  { label: 'Candidata', value: candidateCount, color: 'warning' as const, helper: 'treinada, aguardando governança' },
                  { label: 'Aprovada', value: approvedCount, color: 'success' as const, helper: 'liberada para uso controlado' },
                  { label: 'Rejeitada no registro', value: rejectedCount, color: 'error' as const, helper: 'status final no registry' },
                  { label: 'Rejeitada no gate', value: rejectedGateDecisions.length, color: 'error' as const, helper: 'analisada e bloqueada pelo MUEN' },
                ].map((stage) => (
                  <Paper key={stage.label} elevation={0} sx={{ p: 2, minWidth: 190, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <Stack spacing={0.75}>
                      <Chip size="small" color={stage.color} label={stage.label} sx={{ alignSelf: 'flex-start' }} />
                      <Typography variant="h5" fontWeight={900}>{formatNumber(stage.value)}</Typography>
                      <Typography variant="caption" color="text.secondary">{stage.helper}</Typography>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
              <Typography variant="caption" color="text.secondary">
                A tabela abaixo continua detalhando modelo, versão, métricas e artefato; os cards acima explicam a quantidade por estágio.
              </Typography>
            </Stack>
          </Paper>

          <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <Stack spacing={0.5}>
                <Typography variant="h6" fontWeight={800}>Últimas análises do Gate MUEN</Typography>
                <Typography variant="body2" color="text.secondary">
                  Mostra explicitamente as candidatas que já foram analisadas pelo gate econômico. Assim, uma rede pode continuar como candidata no registry, mas aparecer aqui como rejeitada pelo Gate Research.
                </Typography>
              </Stack>
              {gateDecisionsLoading ? <LinearProgress /> : null}
              {gateDecisionsError ? <Alert severity="warning">Não foi possível carregar as decisões do Gate MUEN.</Alert> : null}
              {!gateDecisionsLoading && !gateDecisionsError && latestGateDecisions.length === 0 ? (
                <Alert severity="info">Ainda não há decisões MUEN registradas para exibir nesta aba.</Alert>
              ) : null}
              {latestGateDecisions.length > 0 ? (
                <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                  <Table size="small" aria-label="Últimas decisões do Gate MUEN em treinos neurais">
                    <TableHead>
                      <TableRow>
                        <TableCell>Decisão</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Família/candidata</TableCell>
                        <TableCell>Critérios</TableCell>
                        <TableCell align="right">Folds +</TableCell>
                        <TableCell align="right">Δ expectancy</TableCell>
                        <TableCell align="right">Drawdown</TableCell>
                        <TableCell>Data</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {latestGateDecisions.map((attempt) => (
                        <TableRow key={attempt.decisionId} hover>
                          <TableCell>
                            <Typography variant="body2" fontWeight={700}>{attempt.decisionId}</Typography>
                          </TableCell>
                          <TableCell><Chip size="small" label={gateStatusLabel(attempt)} color={gateStatusColor(attempt)} /></TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ display: 'block', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {attempt.candidateFamilyHash ?? '—'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ display: 'block', maxWidth: 360 }}>
                              {formatCriteria(attempt.failedCriteria)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">{attempt.positiveFolds ?? '—'} / {attempt.folds ?? '—'}</TableCell>
                          <TableCell align="right">{formatPct(attempt.medianDeltaExpectancyVsChampion)}</TableCell>
                          <TableCell align="right">{formatPct(attempt.maxDrawdown)}</TableCell>
                          <TableCell>{formatDateTime(attempt.decidedAt)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : null}
            </Stack>
          </Paper>

          <Stack direction="row" flexWrap="wrap" gap={2}>
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
                Indicadores da rede mais recente
              </Typography>
              <Typography variant="subtitle2" color="text.secondary">
                Split de treino disponível no registro atual
              </Typography>
              <Stack direction="row" flexWrap="wrap" gap={2}>
                <SummaryCard title="Acurácia treino" value={formatPct(latestTrain?.accuracy)} />
                <SummaryCard
                  title="Precisão direcional treino"
                  value={formatPct(latestTrain?.directionalPrecision)}
                />
                <SummaryCard
                  title="Cobertura treino"
                  value={formatPct(latestTrain?.coverage)}
                />
                <SummaryCard
                  title="Amostras treino"
                  value={formatNumber(latestTrain?.rowsCount)}
                />
              </Stack>
              {typeof latestTrain?.accuracy === 'number' ? (
                <LinearProgress
                  variant="determinate"
                  value={Math.max(0, Math.min(100, latestTrain.accuracy * 100))}
                  sx={{ height: 10, borderRadius: 999 }}
                />
              ) : null}
              <Typography variant="subtitle2" color="text.secondary">
                Split de teste para aprovação futura
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
                  <TableCell align="right">Treino</TableCell>
                  <TableCell align="right">Teste</TableCell>
                  <TableCell align="right">Linhas treino</TableCell>
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
                    <TableCell align="right">{formatPct(splitMetrics(run, 'train').accuracy)}</TableCell>
                    <TableCell align="right">{formatPct(run.testAccuracy)}</TableCell>
                    <TableCell align="right">{formatNumber(splitMetrics(run, 'train').rowsCount)}</TableCell>
                    <TableCell align="right">{formatNumber(splitMetrics(run, 'test').rowsCount)}</TableCell>
                    <TableCell align="right">
                      {formatPct(
                        run.directionalPrecision ??
                          splitMetrics(run, 'test').directionalPrecision ??
                          splitMetrics(run, 'train').directionalPrecision,
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {formatPct(
                        run.coverage ??
                          splitMetrics(run, 'test').coverage ??
                          splitMetrics(run, 'train').coverage,
                      )}
                    </TableCell>
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
