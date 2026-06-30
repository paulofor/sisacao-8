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

const normalizeCandidateKey = (value: string | null | undefined) =>
  value?.trim().toLowerCase() || null

const candidateFamilyHash = (run: NeuralTrainingRun) => {
  const metrics = parseMetricsJson(run.metricsJson)
  const economics = metrics.muen_economics
  const economicsRecord =
    economics && typeof economics === 'object' && !Array.isArray(economics)
      ? (economics as Record<string, unknown>)
      : {}
  const value = economicsRecord.candidate_family_hash ?? economicsRecord.candidateFamilyHash
  return typeof value === 'string' && value.trim() ? value : null
}

const latestRun = (runs: NeuralTrainingRun[]) => runs[0]

const isOnPreviousDay = (value: string | null | undefined) => {
  if (!value) return false
  const parsed = dayjs(value)
  if (!parsed.isValid()) return false
  const previousDay = dayjs().subtract(1, 'day')
  return parsed.isSame(previousDay, 'day')
}

const PHASE3_ARCHITECTURES = [
  'residual_mlp',
  'wide_deep_mlp',
  'tabular_bottleneck_mlp',
]

const isPhase3Run = (run: NeuralTrainingRun) => {
  const searchable = [run.modelId, run.modelVersion, run.metricsJson, run.notes]
    .filter((value): value is string => Boolean(value))
    .join(' ')
    .toLowerCase()

  return (
    searchable.includes('phase3') ||
    searchable.includes('phase3_family') ||
    PHASE3_ARCHITECTURES.some((architecture) => searchable.includes(architecture))
  )
}

const phase3FamilyLabel = (run: NeuralTrainingRun) => {
  const searchable = `${run.modelId ?? ''} ${run.modelVersion ?? ''} ${run.metricsJson ?? ''}`.toLowerCase()
  const architecture = PHASE3_ARCHITECTURES.find((item) => searchable.includes(item))
  if (!architecture) return null
  return architecture.replaceAll('_', ' ')
}

const bestTestAccuracy = (runs: NeuralTrainingRun[]) => {
  const values = runs
    .map((run) => run.testAccuracy)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
  return values.length > 0 ? Math.max(...values) : null
}

interface StageTotal {
  label: string
  value: number
  color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
  helper: string
}

const StageTotalsGroup: FC<{ title: string; subtitle?: string; stages: StageTotal[] }> = ({
  title,
  subtitle,
  stages,
}) => (
  <Stack spacing={1.5}>
    <Stack spacing={0.5}>
      <Typography variant="h6" fontWeight={800}>{title}</Typography>
      {subtitle ? (
        <Typography variant="body2" color="text.secondary">{subtitle}</Typography>
      ) : null}
    </Stack>
    <Stack direction="row" flexWrap="wrap" gap={1.5}>
      {stages.map((stage) => (
        <Paper key={stage.label} elevation={0} sx={{ p: 2, minWidth: 190, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={0.75}>
            <Chip size="small" color={stage.color} label={stage.label} sx={{ alignSelf: 'flex-start' }} />
            <Typography variant="h5" fontWeight={900}>{formatNumber(stage.value)}</Typography>
            <Typography variant="caption" color="text.secondary">{stage.helper}</Typography>
          </Stack>
        </Paper>
      ))}
    </Stack>
  </Stack>
)

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
  const registryTotals = runs[0]
  const previousDay = dayjs().subtract(1, 'day')
  const previousDayLabel = previousDay.format('DD/MM/YYYY')
  const previousDayRuns = runs.filter((run) => isOnPreviousDay(run.trainedAt))
  const previousDayGateDecisions = gateDecisions.filter((attempt) => isOnPreviousDay(attempt.decidedAt))
  const approvedCount = registryTotals?.approvedRuns ?? runs.filter(
    (run) => run.status?.toLowerCase() === 'approved',
  ).length
  const phase3Runs = runs.filter(isPhase3Run)
  const phase3Count = registryTotals?.phase3Runs ?? phase3Runs.length
  const candidateCount = registryTotals?.candidateRuns ?? runs.filter((run) => run.status?.toLowerCase() === 'candidate').length
  const activeTrainingCount = registryTotals?.activeTrainingRuns ?? runs.filter((run) => ['running', 'training', 'in_progress'].includes(run.status?.toLowerCase() ?? '')).length
  const rejectedCount = registryTotals?.rejectedRuns ?? runs.filter((run) => ['rejected', 'reject'].includes(run.status?.toLowerCase() ?? '')).length
  const candidateRuns = runs.filter((run) => run.status?.toLowerCase() === 'candidate')
  const previousDayCandidateRuns = previousDayRuns.filter((run) => run.status?.toLowerCase() === 'candidate')
  const rejectedGateDecisions = gateDecisions.filter((attempt) => attempt.decisionStatus?.toLowerCase() === 'rejected' || attempt.passed === false)
  const previousDayRejectedGateDecisions = previousDayGateDecisions.filter((attempt) => attempt.decisionStatus?.toLowerCase() === 'rejected' || attempt.passed === false)
  const totalRejectedGateDecisions = gateDecisions[0]?.rejectedDecisions ?? rejectedGateDecisions.length
  const evaluatedCandidateKeys = new Set(
    gateDecisions
      .map((attempt) => normalizeCandidateKey(attempt.candidateFamilyHash))
      .filter((value): value is string => Boolean(value)),
  )
  const loadedPendingGateCandidateCount = candidateRuns.filter((run) => {
    const modelVersion = normalizeCandidateKey(run.modelVersion)
    const familyHash = normalizeCandidateKey(candidateFamilyHash(run))
    return !(
      (modelVersion && evaluatedCandidateKeys.has(modelVersion)) ||
      (familyHash && evaluatedCandidateKeys.has(familyHash))
    )
  }).length
  const pendingGateCandidateCount = registryTotals?.pendingGateCandidateRuns ?? loadedPendingGateCandidateCount
  const previousDayEvaluatedCandidateKeys = new Set(
    previousDayGateDecisions
      .map((attempt) => normalizeCandidateKey(attempt.candidateFamilyHash))
      .filter((value): value is string => Boolean(value)),
  )
  const previousDayPendingGateCandidateCount = previousDayCandidateRuns.filter((run) => {
    const modelVersion = normalizeCandidateKey(run.modelVersion)
    const familyHash = normalizeCandidateKey(candidateFamilyHash(run))
    return !(
      (modelVersion && previousDayEvaluatedCandidateKeys.has(modelVersion)) ||
      (familyHash && previousDayEvaluatedCandidateKeys.has(familyHash))
    )
  }).length
  const totalStages: StageTotal[] = [
    { label: 'Em treino', value: activeTrainingCount, color: 'info', helper: 'ainda executando' },
    { label: 'Candidata', value: candidateCount, color: 'warning', helper: 'treinada no registry' },
    { label: 'Fase 3', value: phase3Count, color: 'secondary', helper: 'residual/wide deep/bottleneck' },
    { label: 'Pode ser testada', value: pendingGateCandidateCount, color: 'info', helper: 'sem decisão MUEN carregada' },
    { label: 'Aprovada', value: approvedCount, color: 'success', helper: 'liberada para uso controlado' },
    { label: 'Rejeitada no registro', value: rejectedCount, color: 'error', helper: 'status final no registry' },
    { label: 'Rejeitada no gate', value: totalRejectedGateDecisions, color: 'error', helper: 'analisada e bloqueada pelo MUEN' },
  ]
  const previousDayStages: StageTotal[] = [
    { label: 'Em treino', value: previousDayRuns.filter((run) => ['running', 'training', 'in_progress'].includes(run.status?.toLowerCase() ?? '')).length, color: 'info', helper: 'treinos do dia anterior ainda executando' },
    { label: 'Candidata', value: previousDayCandidateRuns.length, color: 'warning', helper: 'treinada no registry no dia anterior' },
    { label: 'Fase 3', value: previousDayRuns.filter(isPhase3Run).length, color: 'secondary', helper: 'phase3 do dia anterior' },
    { label: 'Pode ser testada', value: previousDayPendingGateCandidateCount, color: 'info', helper: 'sem decisão MUEN no dia anterior' },
    { label: 'Aprovada', value: previousDayRuns.filter((run) => run.status?.toLowerCase() === 'approved').length, color: 'success', helper: 'liberada no dia anterior' },
    { label: 'Rejeitada no registro', value: previousDayRuns.filter((run) => ['rejected', 'reject'].includes(run.status?.toLowerCase() ?? '')).length, color: 'error', helper: 'status final no registry no dia anterior' },
    { label: 'Rejeitada no gate', value: previousDayRejectedGateDecisions.length, color: 'error', helper: 'bloqueada pelo MUEN no dia anterior' },
  ]
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
          <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <StageTotalsGroup title="Como ler o estágio de cada rede" stages={totalStages} />
              <StageTotalsGroup
                title="Totalizações do dia anterior"
                subtitle={`Mesmas contagens limitadas aos treinos e decisões MUEN registrados em ${previousDayLabel}.`}
                stages={previousDayStages}
              />
              <Typography variant="caption" color="text.secondary">
                A contagem “Pode ser testada” cruza candidatas do registry com as decisões MUEN carregadas para estimar quantas ainda não têm decisão de gate. A contagem “Fase 3” identifica redes por prefixo `neural_eod_phase3_`, origem `phase3_family` ou pelas arquiteturas novas residual/wide deep/bottleneck.
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
                        <TableCell>Data</TableCell>
                        <TableCell>Decisão</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Família/candidata</TableCell>
                        <TableCell>Critérios</TableCell>
                        <TableCell align="right">Folds +</TableCell>
                        <TableCell align="right">Δ expectancy</TableCell>
                        <TableCell align="right">Drawdown</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {latestGateDecisions.map((attempt) => (
                        <TableRow key={attempt.decisionId} hover>
                          <TableCell>{formatDateTime(attempt.decidedAt)}</TableCell>
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
                  <TableCell>Fase/família</TableCell>
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
                    <TableCell>
                      {isPhase3Run(run) ? (
                        <Stack spacing={0.25}>
                          <Chip size="small" color="secondary" label="Fase 3" sx={{ alignSelf: 'flex-start' }} />
                          <Typography variant="caption" color="text.secondary">
                            {phase3FamilyLabel(run) ?? 'phase3 family'}
                          </Typography>
                        </Stack>
                      ) : (
                        <Typography variant="caption" color="text.secondary">Anterior</Typography>
                      )}
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
