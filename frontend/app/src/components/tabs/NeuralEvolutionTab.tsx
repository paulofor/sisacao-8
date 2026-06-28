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
  TablePagination,
  TableRow,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState, type FC } from 'react'

import type {
  NeuralEvolutionLeaderboardEntry,
  NeuralGateDecisionAttempt,
  NeuralTrainingRun,
} from '../../api/ops'

interface NeuralEvolutionTabProps {
  leaderboard: NeuralEvolutionLeaderboardEntry[]
  leaderboardError?: Error | null
  leaderboardLoading: boolean
  gateDecisions?: NeuralGateDecisionAttempt[]
  gateDecisionsError?: Error | null
  gateDecisionsLoading?: boolean
  trainingRuns?: NeuralTrainingRun[]
}

interface CandidateFamilySummary {
  familyId: string
  entries: NeuralEvolutionLeaderboardEntry[]
  bestEntry: NeuralEvolutionLeaderboardEntry
  keptCount: number
  rejectedCount: number
  scoreMedian: number | null
  scoreBest: number | null
  stabilityMedian: number | null
  coverageMedian: number | null
  directionalPrecisionMedian: number | null
  createdAt: string | null
}

const formatPct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : '—'

const formatScore = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(value)
    : '—'

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const decisionColor = (decision: string | null) => {
  const normalized = decision?.toLowerCase()
  if (normalized === 'shadow_candidate' || normalized === 'paper_candidate') return 'success'
  if (normalized === 'keep_candidate') return 'info'
  if (normalized === 'reject') return 'error'
  return 'default'
}

const decisionLabel = (decision: string | null | undefined) => {
  const normalized = decision?.toLowerCase()
  if (normalized === 'keep_candidate') return 'Mantida para pesquisa'
  if (normalized === 'shadow_candidate') return 'Elegível ao gate de shadow'
  if (normalized === 'paper_candidate') return 'Elegível ao gate de paper'
  if (normalized === 'reject') return 'Rejeitada nesta etapa'
  return decision ?? 'Sem decisão'
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

const compactJson = (value: string | null | undefined) => {
  if (!value) return '—'
  try {
    return JSON.stringify(JSON.parse(value))
  } catch {
    return value
  }
}

const parseRecord = (value: string | null | undefined): Record<string, unknown> => {
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

const stripSeedFields = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map(stripSeedFields)
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => !['seed', 'random_seed', 'randomSeed'].includes(key))
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, stripSeedFields(item)]),
    )
  }
  return value
}

const familyKey = (entry: NeuralEvolutionLeaderboardEntry) => {
  const architecture = stripSeedFields(parseRecord(entry.architectureJson))
  const hyperparameters = stripSeedFields(parseRecord(entry.hyperparametersJson))
  const serialized = JSON.stringify({ architecture, hyperparameters })
  return serialized === '{"architecture":{},"hyperparameters":{}}'
    ? entry.modelId || entry.modelVersion || entry.candidateId
    : serialized
}

const median = (values: Array<number | null | undefined>) => {
  const numbers = values
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    .sort((left, right) => left - right)
  if (numbers.length === 0) return null
  const midpoint = Math.floor(numbers.length / 2)
  return numbers.length % 2 === 0 ? (numbers[midpoint - 1] + numbers[midpoint]) / 2 : numbers[midpoint]
}

const familyLabel = (index: number, family: CandidateFamilySummary) => {
  const architecture = compactJson(family.bestEntry.architectureJson)
  return architecture === '—' ? `Família ${index + 1}` : `Família ${index + 1} · ${architecture.slice(0, 44)}`
}

const summarizeFamilies = (leaderboard: NeuralEvolutionLeaderboardEntry[]) => {
  const grouped = new Map<string, NeuralEvolutionLeaderboardEntry[]>()
  leaderboard.forEach((entry) => {
    const key = familyKey(entry)
    grouped.set(key, [...(grouped.get(key) ?? []), entry])
  })

  return Array.from(grouped.entries())
    .map(([familyId, entries]): CandidateFamilySummary => {
      const ordered = [...entries].sort((left, right) => (right.scoreTotal ?? Number.NEGATIVE_INFINITY) - (left.scoreTotal ?? Number.NEGATIVE_INFINITY))
      return {
        familyId,
        entries,
        bestEntry: ordered[0],
        keptCount: entries.filter((entry) => entry.decision !== 'reject').length,
        rejectedCount: entries.filter((entry) => entry.decision === 'reject').length,
        scoreMedian: median(entries.map((entry) => entry.scoreTotal)),
        scoreBest: ordered[0]?.scoreTotal ?? null,
        stabilityMedian: median(entries.map((entry) => entry.scoreStability)),
        coverageMedian: median(entries.map((entry) => entry.scoreCoverage)),
        directionalPrecisionMedian: median(entries.map((entry) => entry.scoreDirectionalPrecision)),
        createdAt: ordered[0]?.createdAt ?? null,
      }
    })
    .sort((left, right) => (right.scoreMedian ?? Number.NEGATIVE_INFINITY) - (left.scoreMedian ?? Number.NEGATIVE_INFINITY))
}

const LEADERBOARD_ROWS_PER_PAGE = 20
const FAMILY_ROWS_PER_PAGE = 10
const GATE_DECISION_ROWS = 8

const NeuralEvolutionTab: FC<NeuralEvolutionTabProps> = ({
  leaderboard,
  leaderboardError,
  leaderboardLoading,
  gateDecisions = [],
  gateDecisionsError,
  gateDecisionsLoading = false,
  trainingRuns = [],
}) => {
  const [leaderboardPage, setLeaderboardPage] = useState(0)
  const [familyPage, setFamilyPage] = useState(0)
  const families = useMemo(() => summarizeFamilies(leaderboard), [leaderboard])
  const paginatedFamilies = useMemo(
    () => families.slice(familyPage * FAMILY_ROWS_PER_PAGE, familyPage * FAMILY_ROWS_PER_PAGE + FAMILY_ROWS_PER_PAGE),
    [families, familyPage],
  )
  const paginatedLeaderboard = useMemo(
    () =>
      leaderboard.slice(
        leaderboardPage * LEADERBOARD_ROWS_PER_PAGE,
        leaderboardPage * LEADERBOARD_ROWS_PER_PAGE + LEADERBOARD_ROWS_PER_PAGE,
      ),
    [leaderboard, leaderboardPage],
  )
  const latestRun = leaderboard[0]?.evolutionRunId ?? '—'
  const kept = leaderboard.filter((entry) => entry.decision !== 'reject').length
  const rejected = leaderboard.filter((entry) => entry.decision === 'reject').length
  const evaluatedVersions = new Set(leaderboard.map((entry) => entry.modelVersion))
  const evaluatedModels = evaluatedVersions.size
  const totalCandidates = trainingRuns.length || leaderboard.length
  const waitingEvaluation = Math.max(0, totalCandidates - leaderboard.length)
  const waitingByModelVersion = Math.max(0, totalCandidates - evaluatedModels)
  const bestFamily = families[0]
  const latestGateDecisions = gateDecisions.slice(0, GATE_DECISION_ROWS)

  useEffect(() => {
    setLeaderboardPage(0)
    setFamilyPage(0)
  }, [leaderboard])

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Redes neurais — Famílias e leaderboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Visão por família primeiro: execuções equivalentes são agrupadas por arquitetura e
          hiperparâmetros, desconsiderando seed quando ela aparece na configuração.
        </Typography>
      </Stack>

      {leaderboardLoading ? <Skeleton variant="rounded" height={150} /> : null}
      {leaderboardError ? <Alert severity="error">Erro ao carregar o leaderboard neural.</Alert> : null}
      {!leaderboardLoading && !leaderboardError && leaderboard.length === 0 ? (
        <Alert severity="info">
          Ainda não há candidatos avaliados na evolução neural determinística. Esta tela
          será preenchida automaticamente quando o Cloud Scheduler disparar uma rodada
          real do orquestrador <strong>neural_evolution_orchestrator</strong> sem
          <strong> dry_run</strong> e com treinamento/avaliação concluídos. O disparo manual
          é apenas um adiantamento operacional. A tela lê o leaderboard
          <strong> vw_neural_evolution_leaderboard</strong>; modelos existentes no registro
          de treinos não entram aqui até serem gravados em
          <strong> neural_candidate_evaluations</strong>.
        </Alert>
      ) : null}

      {gateDecisionsLoading ? <Skeleton variant="rounded" height={180} /> : null}
      {gateDecisionsError ? <Alert severity="error">Erro ao carregar as últimas tentativas MUEN.</Alert> : null}
      {!gateDecisionsLoading && !gateDecisionsError ? (
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={2}>
            <Stack spacing={0.5}>
              <Typography variant="h6" fontWeight={800}>Últimas tentativas MUEN</Typography>
              <Typography variant="body2" color="text.secondary">
                Linha do tempo auditável dos gates persistidos pelo orquestrador ou pela avaliação manual.
                Esta seção mostra a decisão, critérios reprovados e métricas agregadas da família.
              </Typography>
            </Stack>

            {latestGateDecisions.length === 0 ? (
              <Alert severity="info">
                Ainda não há decisões MUEN persistidas em <strong>neural_gate_decisions</strong>.
                Quando o Scheduler/orquestrador rodar sem <strong>dry_run</strong>, as tentativas aparecerão aqui.
              </Alert>
            ) : (
              <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                <Table stickyHeader size="small" aria-label="Últimas tentativas MUEN">
                  <TableHead>
                    <TableRow>
                      <TableCell>Decisão</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Família</TableCell>
                      <TableCell>Critérios reprovados</TableCell>
                      <TableCell align="right">Folds</TableCell>
                      <TableCell align="right">Seeds</TableCell>
                      <TableCell align="right">Folds positivos</TableCell>
                      <TableCell align="right">Δ expectancy</TableCell>
                      <TableCell align="right">Drawdown</TableCell>
                      <TableCell align="right">Trades</TableCell>
                      <TableCell>Data</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {latestGateDecisions.map((attempt) => (
                      <TableRow key={attempt.decisionId} hover>
                        <TableCell>
                          <Stack spacing={0.25}>
                            <Typography variant="body2" fontWeight={700}>{attempt.decisionId}</Typography>
                            <Typography variant="caption" color="text.secondary">{attempt.gateName ?? 'Gate MUEN'}</Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Chip size="small" label={gateStatusLabel(attempt)} color={gateStatusColor(attempt)} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" sx={{ display: 'block', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {attempt.candidateFamilyHash ?? '—'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" sx={{ display: 'block', maxWidth: 320 }}>
                            {formatCriteria(attempt.failedCriteria)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{attempt.folds ?? '—'}</TableCell>
                        <TableCell align="right">{attempt.seeds ?? '—'}</TableCell>
                        <TableCell align="right">
                          {attempt.positiveFolds ?? '—'} / {formatPct(attempt.positiveFoldRatio)}
                        </TableCell>
                        <TableCell align="right">{formatPct(attempt.medianDeltaExpectancyVsChampion)}</TableCell>
                        <TableCell align="right">{formatPct(attempt.maxDrawdown)}</TableCell>
                        <TableCell align="right">{attempt.totalTrades ?? '—'}</TableCell>
                        <TableCell>{formatDateTime(attempt.decidedAt)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Stack>
        </Paper>
      ) : null}

      {leaderboard.length > 0 ? (
        <>
          <Alert severity="info">
            <Typography variant="body2" fontWeight={800} gutterBottom>
              Índice de ordenação não é aprovação
            </Typography>
            <Typography variant="body2">
              Famílias agrupam configurações equivalentes. Uma família só avança quando
              mostra consistência em diferentes períodos, seeds e gates. A tabela abaixo
              ordena pesquisa; ela não libera shadow, paper nem operação.
            </Typography>
          </Alert>

          <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Stack spacing={2}>
              <Stack spacing={0.5}>
                <Typography variant="h6" fontWeight={800}>Mapa visual da evolução</Typography>
                <Typography variant="body2" color="text.secondary">
                  Mostra a conta completa: redes no estoque, avaliações feitas, famílias consolidadas e quantas ainda faltam avaliar.
                </Typography>
              </Stack>
              <Stack direction="row" flexWrap="wrap" gap={1.5} alignItems="stretch">
                {[
                  { label: 'Redes no estoque', value: totalCandidates, helper: 'total registrado em Treinos' },
                  { label: 'Avaliações feitas', value: leaderboard.length, helper: 'linhas avaliadas no leaderboard' },
                  { label: 'Famílias', value: families.length, helper: 'agrupadas sem seed' },
                  { label: 'Mantidas', value: kept, helper: 'mantidas para pesquisa' },
                  { label: 'Rejeitadas', value: rejected, helper: 'bloqueadas nesta etapa' },
                  { label: 'Ainda faltam', value: waitingEvaluation, helper: `${totalCandidates} - ${leaderboard.length} avaliações` },
                ].map((stage, index) => (
                  <Box key={stage.label} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        minWidth: 165,
                        border: '1px solid',
                        borderColor: stage.label === 'Rejeitadas' && rejected > 0 ? 'error.light' : 'divider',
                        borderRadius: 2,
                        bgcolor: stage.label === 'Mantidas' && kept > 0 ? 'rgba(46, 125, 50, 0.08)' : stage.label === 'Rejeitadas' && rejected > 0 ? 'rgba(211, 47, 47, 0.08)' : 'background.paper',
                      }}
                    >
                      <Typography variant="overline" color="text.secondary">{stage.label}</Typography>
                      <Typography variant="h4" fontWeight={900}>{stage.value}</Typography>
                      <Typography variant="caption" color="text.secondary">{stage.helper}</Typography>
                    </Paper>
                    {index < 5 ? <Typography color="text.disabled" fontWeight={800}>→</Typography> : null}
                  </Box>
                ))}
              </Stack>
              <Alert severity="info" sx={{ alignItems: 'flex-start' }}>
                <Typography variant="body2" fontWeight={700} gutterBottom>
                  Como ler estes números
                </Typography>
                <Typography variant="body2">
                  Hoje existem <strong>{totalCandidates}</strong> redes registradas em Treinos. O
                  leaderboard tem <strong>{leaderboard.length}</strong> avaliações, agrupadas em
                  <strong> {families.length}</strong> famílias/configurações. Dessas avaliações,
                  <strong> {kept}</strong> estão mantidas para pesquisa e <strong>{rejected}</strong> foram rejeitadas nesta etapa.
                </Typography>
                {evaluatedModels !== leaderboard.length ? (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    Observação técnica: essas {leaderboard.length} avaliações representam {evaluatedModels} versões
                    únicas de modelo. Pela contagem por versão única, ainda seriam {waitingByModelVersion} redes sem
                    versão correspondente avaliada.
                  </Typography>
                ) : null}
              </Alert>
            </Stack>
          </Paper>

          <Stack direction="row" flexWrap="wrap" gap={2}>
            <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 220 }}>
              <Typography variant="overline" color="text.secondary">Melhor família</Typography>
              <Typography variant="body2" fontWeight={800}>{bestFamily ? familyLabel(0, bestFamily) : '—'}</Typography>
              <Typography variant="caption" color="text.secondary">Mediana do índice: {formatScore(bestFamily?.scoreMedian)}</Typography>
            </Paper>
            <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 220 }}>
              <Typography variant="overline" color="text.secondary">Rodada</Typography>
              <Typography variant="body2" fontWeight={800}>{latestRun}</Typography>
            </Paper>
          </Stack>

          <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Table stickyHeader size="small" aria-label="Famílias candidatas de evolução neural">
              <TableHead>
                <TableRow>
                  <TableCell>Família</TableCell>
                  <TableCell>Melhor modelo</TableCell>
                  <TableCell>Gate atual</TableCell>
                  <TableCell align="right">Execuções</TableCell>
                  <TableCell align="right">Mantidas</TableCell>
                  <TableCell align="right">Rejeitadas</TableCell>
                  <TableCell align="right">Índice mediano</TableCell>
                  <TableCell align="right">Melhor índice</TableCell>
                  <TableCell align="right">Precisão dir.</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell align="right">Estabilidade</TableCell>
                  <TableCell>Próximo passo</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedFamilies.map((family, index) => {
                  const absoluteIndex = familyPage * FAMILY_ROWS_PER_PAGE + index
                  const bestDecision = family.bestEntry.decision
                  const blocked = family.keptCount === 0
                  return (
                    <TableRow key={family.familyId} hover>
                      <TableCell>
                        <Stack spacing={0.25}>
                          <Typography variant="body2" fontWeight={700}>{familyLabel(absoluteIndex, family)}</Typography>
                          <Typography variant="caption" color="text.secondary">Criada em {formatDateTime(family.createdAt)}</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack spacing={0.25}>
                          <Typography variant="body2" fontWeight={700}>{family.bestEntry.modelId}</Typography>
                          <Typography variant="caption" color="text.secondary">{family.bestEntry.modelVersion}</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell><Chip size="small" label={decisionLabel(bestDecision)} color={decisionColor(bestDecision)} /></TableCell>
                      <TableCell align="right">{family.entries.length}</TableCell>
                      <TableCell align="right">{family.keptCount}</TableCell>
                      <TableCell align="right">{family.rejectedCount}</TableCell>
                      <TableCell align="right">{formatScore(family.scoreMedian)}</TableCell>
                      <TableCell align="right">{formatScore(family.scoreBest)}</TableCell>
                      <TableCell align="right">{formatPct(family.directionalPrecisionMedian)}</TableCell>
                      <TableCell align="right">{formatPct(family.coverageMedian)}</TableCell>
                      <TableCell align="right">{formatPct(family.stabilityMedian)}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {blocked
                            ? 'Revisar motivos de rejeição antes de nova rodada.'
                            : 'Confirmar folds/seeds e avaliar gates MUEN antes de holdout.'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={families.length}
              page={familyPage}
              onPageChange={(_, nextPage) => setFamilyPage(nextPage)}
              rowsPerPage={FAMILY_ROWS_PER_PAGE}
              rowsPerPageOptions={[FAMILY_ROWS_PER_PAGE]}
              labelRowsPerPage="Famílias por página"
              labelDisplayedRows={({ from, to, count }) =>
                `${from}–${to} de ${count !== -1 ? count : `mais de ${to}`}`
              }
            />
          </TableContainer>

          <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Table stickyHeader size="small" aria-label="Execuções individuais do leaderboard neural">
              <TableHead>
                <TableRow>
                  <TableCell>Rank</TableCell>
                  <TableCell>Modelo</TableCell>
                  <TableCell>Decisão</TableCell>
                  <TableCell align="right">Índice de ordenação</TableCell>
                  <TableCell align="right">Precisão dir.</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell align="right">Generalização</TableCell>
                  <TableCell align="right">Estabilidade</TableCell>
                  <TableCell>Configuração</TableCell>
                  <TableCell>Criado em</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedLeaderboard.map((entry) => (
                  <TableRow key={entry.candidateId} hover>
                    <TableCell>{entry.rankInRun ?? '—'}</TableCell>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2" fontWeight={700}>{entry.modelId}</Typography>
                        <Typography variant="caption" color="text.secondary">{entry.modelVersion}</Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={decisionLabel(entry.decision)} color={decisionColor(entry.decision)} />
                    </TableCell>
                    <TableCell align="right">{formatScore(entry.scoreTotal)}</TableCell>
                    <TableCell align="right">{formatPct(entry.scoreDirectionalPrecision)}</TableCell>
                    <TableCell align="right">{formatPct(entry.scoreCoverage)}</TableCell>
                    <TableCell align="right">{formatPct(entry.scoreGeneralization)}</TableCell>
                    <TableCell align="right">{formatPct(entry.scoreStability)}</TableCell>
                    <TableCell title={`${entry.architectureJson ?? ''}\n${entry.hyperparametersJson ?? ''}`}>
                      <Typography variant="caption" sx={{ display: 'block', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {compactJson(entry.hyperparametersJson)}
                      </Typography>
                    </TableCell>
                    <TableCell>{formatDateTime(entry.createdAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={leaderboard.length}
              page={leaderboardPage}
              onPageChange={(_, nextPage) => setLeaderboardPage(nextPage)}
              rowsPerPage={LEADERBOARD_ROWS_PER_PAGE}
              rowsPerPageOptions={[LEADERBOARD_ROWS_PER_PAGE]}
              labelRowsPerPage="Execuções por página"
              labelDisplayedRows={({ from, to, count }) =>
                `${from}–${to} de ${count !== -1 ? count : `mais de ${to}`}`
              }
            />
          </TableContainer>
        </>
      ) : null}
    </Stack>
  )
}

export default NeuralEvolutionTab
