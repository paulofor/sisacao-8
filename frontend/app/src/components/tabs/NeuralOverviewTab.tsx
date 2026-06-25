import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked'
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type {
  NeuralEvolutionLeaderboardEntry,
  NeuralTrainingDataAllocation,
  NeuralTrainingRun,
  QuantBaselineStrategy,
} from '../../api/ops'
import { buildNeuralBaselineReadiness } from './neuralBaselineReadiness'

type NeuralNavigationTarget = 'neural-training-data' | 'neural-training-runs' | 'neural-evolution' | 'ai-advisor' | 'quant-roadmap'

interface NeuralOverviewTabProps {
  allocation: NeuralTrainingDataAllocation[]
  allocationError?: Error | null
  allocationLoading: boolean
  leaderboard: NeuralEvolutionLeaderboardEntry[]
  leaderboardError?: Error | null
  leaderboardLoading: boolean
  onNavigate: (target: NeuralNavigationTarget) => void
  quantBaselineStrategies: QuantBaselineStrategy[]
  quantBaselineStrategiesError?: Error | null
  quantBaselineStrategiesLoading: boolean
  trainingRuns: NeuralTrainingRun[]
  trainingRunsError?: Error | null
  trainingRunsLoading: boolean
}

type JourneyStatus = 'done' | 'running' | 'waiting' | 'blocked'

interface JourneyStage {
  label: string
  status: JourneyStatus
  summary: string
  countLabel: string
}

const statusMeta: Record<JourneyStatus, { label: string; color: 'success' | 'info' | 'warning' | 'error'; icon: typeof CheckCircleIcon }> = {
  done: { label: 'Concluído', color: 'success', icon: CheckCircleIcon },
  running: { label: 'Em andamento', color: 'info', icon: PlayCircleOutlineIcon },
  waiting: { label: 'Aguardando', color: 'warning', icon: HourglassEmptyIcon },
  blocked: { label: 'Bloqueado', color: 'error', icon: ErrorOutlineIcon },
}

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR').format(value)
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

const translatedDecision = (decision: string | null | undefined) => {
  const normalized = decision?.toLowerCase()
  if (normalized === 'keep_candidate') return 'Mantida para pesquisa'
  if (normalized === 'shadow_candidate') return 'Elegível ao gate de shadow'
  if (normalized === 'paper_candidate') return 'Elegível ao gate de paper'
  if (normalized === 'reject') return 'Rejeitada nesta etapa'
  return decision ?? 'Sem decisão'
}

const familyKey = (entry: NeuralEvolutionLeaderboardEntry) => {
  const config = [entry.architectureJson, entry.hyperparametersJson].filter(Boolean).join('|')
  return config || entry.modelId || entry.modelVersion || entry.candidateId
}

const statusCount = (runs: NeuralTrainingRun[], statuses: string[]) => {
  const accepted = new Set(statuses.map((status) => status.toLowerCase()))
  return runs.filter((run) => accepted.has(run.status?.toLowerCase() ?? '')).length
}

const SummaryCard: FC<{ title: string; value: string; helper: string; tone?: 'default' | 'success' | 'warning' | 'error' }> = ({
  title,
  value,
  helper,
  tone = 'default',
}) => {
  const toneColor = tone === 'success' ? 'success.light' : tone === 'warning' ? 'warning.light' : tone === 'error' ? 'error.light' : 'divider'
  return (
    <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: toneColor, borderRadius: 2, flex: 1, minWidth: 210 }}>
      <Stack spacing={0.75}>
        <Typography variant="overline" color="text.secondary">{title}</Typography>
        <Typography variant="h5" fontWeight={900}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{helper}</Typography>
      </Stack>
    </Paper>
  )
}

const buildJourney = (
  allocation: NeuralTrainingDataAllocation[],
  runs: NeuralTrainingRun[],
  leaderboard: NeuralEvolutionLeaderboardEntry[],
  quantBaselineStrategies: QuantBaselineStrategy[],
): JourneyStage[] => {
  const totalRows = allocation.reduce((total, row) => total + row.rowsCount, 0)
  const evaluatedCount = leaderboard.length
  const keptCount = leaderboard.filter((entry) => entry.decision !== 'reject').length
  const shadowReady = leaderboard.some((entry) => ['shadow_candidate', 'paper_candidate'].includes(entry.decision?.toLowerCase() ?? ''))
  const hasData = totalRows > 0
  const hasRuns = runs.length > 0
  const baselineReadiness = buildNeuralBaselineReadiness(quantBaselineStrategies, runs, leaderboard)

  return [
    { label: 'Hipótese', status: 'done', summary: 'MUEN v1 registrado como contrato de evolução neural EOD.', countLabel: '1 protocolo' },
    { label: 'Dados', status: hasData ? 'done' : 'waiting', summary: hasData ? 'Snapshot de treino disponível para inspeção.' : 'Aguardando materialização do snapshot.', countLabel: `${formatNumber(totalRows)} linhas` },
    { label: 'Labels', status: hasData ? 'done' : 'waiting', summary: hasData ? 'Distribuição BUY/SELL/NEUTRAL disponível nos dados atuais.' : 'Labels dependem do snapshot.', countLabel: `${formatNumber(allocation.length)} splits` },
    { label: 'Baselines', status: baselineReadiness.status, summary: baselineReadiness.summary, countLabel: baselineReadiness.countLabel },
    { label: 'Experimentos', status: hasRuns ? 'running' : 'waiting', summary: hasRuns ? 'Artefatos treinados já existem para acompanhamento.' : 'Nenhum treino carregado.', countLabel: `${formatNumber(runs.length)} redes` },
    { label: 'Walk-forward', status: evaluatedCount > 0 ? 'running' : 'waiting', summary: evaluatedCount > 0 ? 'Leaderboard atual consolida avaliações disponíveis.' : 'Aguardando avaliações da evolução.', countLabel: `${formatNumber(evaluatedCount)} avaliações` },
    { label: 'Holdout', status: keptCount > 0 ? 'waiting' : 'blocked', summary: keptCount > 0 ? 'Há candidatas mantidas, mas holdout segue governado.' : 'Sem família elegível para abertura.', countLabel: `${formatNumber(keptCount)} mantidas` },
    { label: 'Shadow', status: shadowReady ? 'waiting' : 'blocked', summary: shadowReady ? 'Existe candidata elegível ao gate de shadow.' : 'Nenhuma candidata pode gerar sinais shadow ainda.', countLabel: shadowReady ? 'gate possível' : 'sem gate' },
    { label: 'Paper', status: leaderboard.some((entry) => entry.decision?.toLowerCase() === 'paper_candidate') ? 'waiting' : 'blocked', summary: 'Paper exige confirmação prospectiva antes de qualquer capital real.', countLabel: 'sem capital real' },
    { label: 'Promoção', status: 'blocked', summary: 'Promoção controlada exige gates, fallback e aprovação humana.', countLabel: 'bloqueada' },
  ]
}

const NeuralOverviewTab: FC<NeuralOverviewTabProps> = ({
  allocation,
  allocationError,
  allocationLoading,
  leaderboard,
  leaderboardError,
  leaderboardLoading,
  onNavigate,
  quantBaselineStrategies,
  quantBaselineStrategiesError,
  quantBaselineStrategiesLoading,
  trainingRuns,
  trainingRunsError,
  trainingRunsLoading,
}) => {
  const loading = allocationLoading || leaderboardLoading || trainingRunsLoading || quantBaselineStrategiesLoading
  const hasError = allocationError || leaderboardError || trainingRunsError || quantBaselineStrategiesError
  const totalRows = allocation.reduce((total, row) => total + row.rowsCount, 0)
  const familiesCount = new Set(leaderboard.map(familyKey)).size
  const kept = leaderboard.filter((entry) => entry.decision !== 'reject').length
  const rejected = leaderboard.filter((entry) => entry.decision === 'reject').length
  const baselineReadiness = buildNeuralBaselineReadiness(quantBaselineStrategies, trainingRuns, leaderboard)
  const champion = baselineReadiness.champion
  const bestChallenger = baselineReadiness.bestChallenger
  const runningTrials = statusCount(trainingRuns, ['running', 'training', 'in_progress'])
  const latestUpdate = [
    ...trainingRuns.map((run) => run.trainedAt ?? run.createdAt),
    ...leaderboard.map((entry) => entry.createdAt),
  ]
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => dayjs(right).valueOf() - dayjs(left).valueOf())[0]
  const journey = buildJourney(allocation, trainingRuns, leaderboard, quantBaselineStrategies)

  const nowText = leaderboard.length > 0
    ? `O SisAção tem ${formatNumber(familiesCount)} famílias/configurações avaliadas no leaderboard atual. A melhor challenger é ${bestChallenger?.modelVersion ?? '—'} e ${formatNumber(kept)} candidatas permanecem mantidas para pesquisa.`
    : trainingRuns.length > 0
      ? `O SisAção possui ${formatNumber(trainingRuns.length)} redes registradas em Treinos, mas ainda não há avaliações suficientes no leaderboard para selecionar uma challenger.`
      : 'O SisAção está aguardando treinos e avaliações neurais para preencher a jornada MUEN.'

  const nextStep = leaderboard.length > 0
    ? 'Consolidar famílias por arquitetura/hiperparâmetros, validar folds/seeds e só então avaliar elegibilidade a holdout.'
    : trainingRuns.length > 0
      ? 'Executar ou aguardar a evolução determinística para preencher avaliações, decisões e melhor challenger.'
      : 'Materializar dados, executar treinos e registrar avaliações antes de qualquer gate promocional.'

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Stack direction="row" flexWrap="wrap" gap={1} alignItems="center">
          <Typography variant="h4" gutterBottom color="text.primary">Evolução neural EOD</Typography>
          <Chip label="Pesquisa" color="info" size="small" />
          <Chip label="Sem capital real" color="success" variant="outlined" size="small" />
        </Stack>
        <Typography variant="body1" color="text.secondary">
          Visão geral da jornada MUEN: processo primeiro, ranking depois. A pontuação ordena candidatas, mas não aprova shadow, paper ou operação.
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Última evidência carregada: {formatDateTime(latestUpdate)} · Protocol version: neural_eod_protocol_v1 · Dataset snapshot: {allocation[0]?.featureVersion ?? bestChallenger?.datasetSnapshot ?? '—'}
        </Typography>
      </Stack>

      {loading ? <Skeleton variant="rounded" height={160} /> : null}
      {hasError ? <Alert severity="warning">Alguns blocos da visão geral não puderam carregar. Os dados disponíveis continuam sendo exibidos.</Alert> : null}

      <Alert severity="info" icon={<InfoOutlinedIcon />}>
        <Typography variant="body2" fontWeight={800}>Score não é aprovação</Typography>
        <Typography variant="body2">O índice de ordenação ajuda a priorizar candidatos. Avanço para holdout, shadow, paper ou operação exige gates, evidências e aprovação humana.</Typography>
      </Alert>

      <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6" fontWeight={900}>Jornada passo a passo</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(5, minmax(0, 1fr))' }, gap: 1.5 }}>
            {journey.map((stage) => {
              const meta = statusMeta[stage.status]
              const Icon = meta.icon ?? RadioButtonUncheckedIcon
              return (
                <Paper key={stage.label} elevation={0} sx={{ p: 1.75, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                  <Stack spacing={1}>
                    <Stack direction="row" justifyContent="space-between" gap={1} alignItems="center">
                      <Typography variant="subtitle2" fontWeight={900}>{stage.label}</Typography>
                      <Chip size="small" icon={<Icon />} label={meta.label} color={meta.color} variant={stage.status === 'done' ? 'filled' : 'outlined'} />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">{stage.summary}</Typography>
                    <Typography variant="caption" color="text.secondary">{stage.countLabel}</Typography>
                  </Stack>
                </Paper>
              )
            })}
          </Box>
        </Stack>
      </Paper>

      <Stack direction="row" flexWrap="wrap" gap={2}>
        <SummaryCard title="Linhas no snapshot" value={formatNumber(totalRows)} helper="dados e labels carregados" />
        <SummaryCard title="Redes no estoque" value={formatNumber(trainingRuns.length)} helper="artefatos registrados em Treinos" />
        <SummaryCard title="Famílias avaliadas" value={formatNumber(familiesCount)} helper="configurações distintas no leaderboard" />
        <SummaryCard title="Baselines econômicos" value={formatNumber(baselineReadiness.baselineCount)} helper={`${formatNumber(baselineReadiness.baselinesWithEconomicMetrics)} com métrica · ${formatNumber(baselineReadiness.positiveBaselines)} positivos`} tone={baselineReadiness.formalComparisonReady ? 'success' : 'warning'} />
        <SummaryCard title="Mantidas" value={formatNumber(kept)} helper="mantidas para pesquisa, não aprovadas" tone="success" />
        <SummaryCard title="Rejeitadas" value={formatNumber(rejected)} helper="bloqueadas nesta etapa" tone={rejected > 0 ? 'error' : 'default'} />
        <SummaryCard title="Trials em execução" value={formatNumber(runningTrials)} helper="running/training/in_progress" tone={runningTrials > 0 ? 'warning' : 'default'} />
      </Stack>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(3, 1fr)' }, gap: 2 }}>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1.25}>
            <Typography variant="h6" fontWeight={900}>Champion atual</Typography>
            {champion ? (
              <>
                <Typography variant="h5" fontWeight={900}>{champion.modelVersion}</Typography>
                <Typography variant="body2" color="text.secondary">Modelo {champion.modelId} · status {champion.status}</Typography>
                <Typography variant="caption" color="text.secondary">Aprovado no registro de treinos; ainda sujeito aos gates MUEN antes de qualquer exposição real.</Typography>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">Nenhum champion aprovado foi encontrado nos dados atuais.</Typography>
            )}
          </Stack>
        </Paper>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1.25}>
            <Typography variant="h6" fontWeight={900}>Baseline econômico líder</Typography>
            {baselineReadiness.bestEconomicBaseline ? (
              <>
                <Typography variant="h5" fontWeight={900}>{baselineReadiness.bestEconomicBaseline.strategyId}</Typography>
                <Typography variant="body2" color="text.secondary">Expectancy líquida: {formatScore(baselineReadiness.bestEconomicBaseline.expectancyNetPct)}% · trades: {formatNumber(baselineReadiness.bestEconomicBaseline.trades)}</Typography>
                <Typography variant="caption" color="text.secondary">Status: {baselineReadiness.bestEconomicBaseline.computedStatus ?? baselineReadiness.bestEconomicBaseline.configuredStatus ?? '—'} · robustez: {formatScore(baselineReadiness.bestEconomicBaseline.robustnessScore)}</Typography>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">Nenhum baseline econômico com expectancy carregada ainda.</Typography>
            )}
            <Typography variant="caption" color="text.secondary">{baselineReadiness.nextStep}</Typography>
          </Stack>
        </Paper>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1.25}>
            <Typography variant="h6" fontWeight={900}>Melhor challenger</Typography>
            {bestChallenger ? (
              <>
                <Typography variant="h5" fontWeight={900}>{bestChallenger.modelVersion}</Typography>
                <Typography variant="body2" color="text.secondary">Índice de ordenação: {formatScore(bestChallenger.scoreTotal)} · {translatedDecision(bestChallenger.decision)}</Typography>
                <Typography variant="caption" color="text.secondary">Candidate ID: {bestChallenger.candidateId}</Typography>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">Nenhuma challenger avaliada no leaderboard atual.</Typography>
            )}
          </Stack>
        </Paper>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.2fr 0.8fr' }, gap: 2 }}>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1}>
            <Typography variant="h6" fontWeight={900}>O que está acontecendo agora?</Typography>
            <Typography variant="body2" color="text.secondary">{nowText}</Typography>
          </Stack>
        </Paper>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1}>
            <Typography variant="h6" fontWeight={900}>Próximo passo seguro</Typography>
            <Typography variant="body2" color="text.secondary">{nextStep}</Typography>
          </Stack>
        </Paper>
      </Box>

      <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={1.5}>
          <Typography variant="h6" fontWeight={900}>Acessos rápidos</Typography>
          <Stack direction="row" flexWrap="wrap" gap={1}>
            <Tooltip title="Ver snapshot, distribuição e qualidade dos dados de treino."><Button variant="outlined" onClick={() => onNavigate('neural-training-data')}>Dados e protocolo</Button></Tooltip>
            <Tooltip title="Abrir artefatos treinados e métricas por execução."><Button variant="outlined" onClick={() => onNavigate('neural-training-runs')}>Treinos</Button></Tooltip>
            <Tooltip title="Abrir ranking atual, mantendo a leitura de score apenas como ordenação."><Button variant="outlined" onClick={() => onNavigate('neural-evolution')}>Famílias e leaderboard</Button></Tooltip>
            <Tooltip title="Abrir a tela quantitativa com baselines econômicos já disponíveis."><Button variant="outlined" onClick={() => onNavigate('quant-roadmap')}>Baselines econômicos</Button></Tooltip>
            <Tooltip title="Solicitar sugestões sem delegar decisão de promoção ao advisor."><Button variant="outlined" onClick={() => onNavigate('ai-advisor')}>Advisor IA</Button></Tooltip>
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  )
}

export default NeuralOverviewTab
