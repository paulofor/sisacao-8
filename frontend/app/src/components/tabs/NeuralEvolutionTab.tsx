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
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { NeuralEvolutionLeaderboardEntry, NeuralTrainingRun } from '../../api/ops'

interface NeuralEvolutionTabProps {
  leaderboard: NeuralEvolutionLeaderboardEntry[]
  leaderboardError?: Error | null
  leaderboardLoading: boolean
  trainingRuns?: NeuralTrainingRun[]
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

const compactJson = (value: string | null | undefined) => {
  if (!value) return '—'
  try {
    return JSON.stringify(JSON.parse(value))
  } catch {
    return value
  }
}

const NeuralEvolutionTab: FC<NeuralEvolutionTabProps> = ({
  leaderboard,
  leaderboardError,
  leaderboardLoading,
  trainingRuns = [],
}) => {
  const latestRun = leaderboard[0]?.evolutionRunId ?? '—'
  const kept = leaderboard.filter((entry) => entry.decision !== 'reject').length
  const rejected = leaderboard.filter((entry) => entry.decision === 'reject').length
  const evaluatedVersions = new Set(leaderboard.map((entry) => entry.modelVersion))
  const waitingEvaluation = Math.max(0, trainingRuns.length - evaluatedVersions.size)

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Redes neurais — Evolução determinística
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Ranking dos candidatos da Fase 1 com score ponderado, métricas fora da amostra,
          decisão automática de governança e rastreabilidade de configuração.
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

      {leaderboard.length > 0 ? (
        <>
          <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Stack spacing={2}>
              <Stack spacing={0.5}>
                <Typography variant="h6" fontWeight={800}>Mapa visual da evolução</Typography>
                <Typography variant="body2" color="text.secondary">
                  Diferencia o estoque total de redes candidatas do subconjunto efetivamente avaliado nesta rodada.
                </Typography>
              </Stack>
              <Stack direction="row" flexWrap="wrap" gap={1.5} alignItems="stretch">
                {[
                  { label: 'Redes candidatas', value: trainingRuns.length || leaderboard.length, helper: 'registradas em Treinos' },
                  { label: 'Aguardando avaliação', value: waitingEvaluation, helper: 'não entraram nesta rodada' },
                  { label: 'Avaliadas agora', value: leaderboard.length, helper: latestRun },
                  { label: 'Mantidas', value: kept, helper: 'seguem no funil' },
                  { label: 'Rejeitadas', value: rejected, helper: 'bloqueadas pela governança' },
                ].map((stage, index) => (
                  <Box key={stage.label} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        minWidth: 170,
                        border: '1px solid',
                        borderColor: index === 4 && rejected > 0 ? 'error.light' : 'divider',
                        borderRadius: 2,
                        bgcolor: index === 3 && kept > 0 ? 'rgba(46, 125, 50, 0.08)' : index === 4 && rejected > 0 ? 'rgba(211, 47, 47, 0.08)' : 'background.paper',
                      }}
                    >
                      <Typography variant="overline" color="text.secondary">{stage.label}</Typography>
                      <Typography variant="h4" fontWeight={900}>{stage.value}</Typography>
                      <Typography variant="caption" color="text.secondary">{stage.helper}</Typography>
                    </Paper>
                    {index < 4 ? <Typography color="text.disabled" fontWeight={800}>→</Typography> : null}
                  </Box>
                ))}
              </Stack>
            </Stack>
          </Paper>

          <Stack direction="row" flexWrap="wrap" gap={2}>
            <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 220 }}>
              <Typography variant="overline" color="text.secondary">Melhor score</Typography>
              <Typography variant="h5" fontWeight={800}>{formatScore(leaderboard[0]?.scoreTotal)}</Typography>
            </Paper>
            <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 220 }}>
              <Typography variant="overline" color="text.secondary">Rodada</Typography>
              <Typography variant="body2" fontWeight={800}>{latestRun}</Typography>
            </Paper>
          </Stack>

          <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Table stickyHeader size="small" aria-label="Leaderboard de evolução neural">
              <TableHead>
                <TableRow>
                  <TableCell>Rank</TableCell>
                  <TableCell>Modelo</TableCell>
                  <TableCell>Decisão</TableCell>
                  <TableCell align="right">Score</TableCell>
                  <TableCell align="right">Precisão dir.</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell align="right">Generalização</TableCell>
                  <TableCell align="right">Estabilidade</TableCell>
                  <TableCell>Configuração</TableCell>
                  <TableCell>Criado em</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {leaderboard.map((entry) => (
                  <TableRow key={entry.candidateId} hover>
                    <TableCell>{entry.rankInRun ?? '—'}</TableCell>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2" fontWeight={700}>{entry.modelId}</Typography>
                        <Typography variant="caption" color="text.secondary">{entry.modelVersion}</Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={entry.decision ?? '—'} color={decisionColor(entry.decision)} />
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
          </TableContainer>
        </>
      ) : null}
    </Stack>
  )
}

export default NeuralEvolutionTab
