import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import LockOutlinedIcon from '@mui/icons-material/LockOutlined'
import PendingOutlinedIcon from '@mui/icons-material/PendingOutlined'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Stack,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { useMemo, useState, type FC } from 'react'

import type {
  NeuralEvolutionLeaderboardEntry,
  NeuralTrainingDataAllocation,
  NeuralTrainingRun,
  QuantBaselineStrategy,
} from '../../api/ops'
import { buildNeuralBaselineReadiness } from './neuralBaselineReadiness'

interface NeuralJourneyTabProps {
  allocation: NeuralTrainingDataAllocation[]
  allocationError?: Error | null
  allocationLoading: boolean
  leaderboard: NeuralEvolutionLeaderboardEntry[]
  leaderboardError?: Error | null
  leaderboardLoading: boolean
  quantBaselineStrategies: QuantBaselineStrategy[]
  quantBaselineStrategiesError?: Error | null
  quantBaselineStrategiesLoading: boolean
  trainingRuns: NeuralTrainingRun[]
  trainingRunsError?: Error | null
  trainingRunsLoading: boolean
}

type JourneyState = 'done' | 'running' | 'waiting' | 'blocked'

interface JourneyStepModel {
  title: string
  state: JourneyState
  evidence: string[]
  visualChecklist?: Array<{ label: string; ready: boolean; detail: string }>
  blockerSummary?: string
  interpretation: {
    objective: string
    entryCriteria: string
    exitCriteria: string
    risks: string
    nextStep: string
  }
}

const stateMeta: Record<JourneyState, { label: string; color: 'success' | 'info' | 'warning' | 'error'; icon: typeof CheckCircleIcon }> = {
  done: { label: 'Concluído', color: 'success', icon: CheckCircleIcon },
  running: { label: 'Em andamento', color: 'info', icon: PlayCircleOutlineIcon },
  waiting: { label: 'Aguardando', color: 'warning', icon: PendingOutlinedIcon },
  blocked: { label: 'Bloqueado', color: 'error', icon: LockOutlinedIcon },
}

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR').format(value)
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

const statusCount = (runs: NeuralTrainingRun[], statuses: string[]) => {
  const accepted = new Set(statuses.map((status) => status.toLowerCase()))
  return runs.filter((run) => accepted.has(run.status?.toLowerCase() ?? '')).length
}

const buildJourneySteps = (
  allocation: NeuralTrainingDataAllocation[],
  trainingRuns: NeuralTrainingRun[],
  leaderboard: NeuralEvolutionLeaderboardEntry[],
  quantBaselineStrategies: QuantBaselineStrategy[],
): JourneyStepModel[] => {
  const totalRows = allocation.reduce((total, row) => total + row.rowsCount, 0)
  const tickers = allocation.reduce((total, row) => Math.max(total, row.tickersCount), 0)
  const minDate = allocation.map((row) => row.minReferenceDate).filter(Boolean).sort()[0]
  const maxDate = allocation.map((row) => row.maxReferenceDate).filter(Boolean).sort().at(-1)
  const upCount = allocation.reduce((total, row) => total + row.upCount, 0)
  const downCount = allocation.reduce((total, row) => total + row.downCount, 0)
  const neutralCount = allocation.reduce((total, row) => total + row.neutralCount, 0)
  const activeRuns = statusCount(trainingRuns, ['running', 'training', 'in_progress'])
  const failedRuns = statusCount(trainingRuns, ['failed', 'error'])
  const evaluated = leaderboard.length
  const kept = leaderboard.filter((entry) => entry.decision !== 'reject').length
  const shadowReady = leaderboard.some((entry) => ['shadow_candidate', 'paper_candidate'].includes(entry.decision?.toLowerCase() ?? ''))
  const paperReady = leaderboard.some((entry) => entry.decision?.toLowerCase() === 'paper_candidate')
  const latestRun = trainingRuns[0]
  const baselineReadiness = buildNeuralBaselineReadiness(quantBaselineStrategies, trainingRuns, leaderboard)

  return [
    {
      title: 'Passo 1 — Hipótese',
      state: 'done',
      evidence: [
        'Hipótese econômica: EOD barrier direction para BUY/SELL.',
        'Protocolo atual: neural_eod_protocol_v1.',
        'Status: aprovado para pesquisa; sem liberação de capital real.',
      ],
      interpretation: {
        objective: 'Fixar a pergunta econômica antes de treinar ou promover modelos.',
        entryCriteria: 'Hipótese, universo, horizonte, entradas, target, stop e custos definidos.',
        exitCriteria: 'Contrato de pesquisa congelado o suficiente para gerar dados e labels.',
        risks: 'Mudar hipótese depois de ver resultados cria viés e invalida comparação.',
        nextStep: 'Manter alterações de hipótese apenas em novo protocolo versionado.',
      },
    },
    {
      title: 'Passo 2 — Dados',
      state: totalRows > 0 ? 'done' : 'waiting',
      evidence: [
        `Linhas no snapshot atual: ${formatNumber(totalRows)}.`,
        `Ativos cobertos: ${formatNumber(tickers)}.`,
        `Período observado: ${formatDate(minDate)} até ${formatDate(maxDate)}.`,
        `Feature version: ${allocation[0]?.featureVersion ?? '—'} · Label version: ${allocation[0]?.labelVersion ?? '—'}.`,
      ],
      interpretation: {
        objective: 'Deixar claro com qual snapshot point-in-time a pesquisa foi construída.',
        entryCriteria: 'Snapshot materializado, versões de features/labels e período conhecidos.',
        exitCriteria: 'Dados completos o bastante para treino e validação temporal.',
        risks: 'Dataset incompleto, desatualizado ou não point-in-time pode contaminar resultados.',
        nextStep: totalRows > 0 ? 'Usar a tela Dados de treino para revisar qualidade e distribuição.' : 'Materializar o snapshot neural antes de avançar.',
      },
    },
    {
      title: 'Passo 3 — Labels',
      state: totalRows > 0 ? 'done' : 'waiting',
      evidence: [
        `Labels BUY/UP: ${formatNumber(upCount)}.`,
        `Labels SELL/DOWN: ${formatNumber(downCount)}.`,
        `Neutros/sem entrada: ${formatNumber(neutralCount)}.`,
        `Distribuição BUY: ${formatPct(totalRows ? upCount / totalRows : null)} · SELL: ${formatPct(totalRows ? downCount / totalRows : null)}.`,
      ],
      interpretation: {
        objective: 'Verificar se os labels representam a regra de trade e se há equilíbrio mínimo.',
        entryCriteria: 'Label version definida e motor de execução compartilhado com backtest.',
        exitCriteria: 'Distribuição compreendida e paridade label/backtest preservada.',
        risks: 'Ambiguidade de target/stop no mesmo candle ou label sem paridade operacional.',
        nextStep: 'Conferir flags de qualidade e manter a política de ambiguidade documentada.',
      },
    },
    {
      title: 'Passo 4 — Baselines',
      state: baselineReadiness.status,
      evidence: baselineReadiness.evidence,
      visualChecklist: baselineReadiness.gateChecklist,
      blockerSummary: baselineReadiness.blockerSummary,
      interpretation: {
        objective: 'Garantir que a rede neural supere referências simples e robustas.',
        entryCriteria: 'Heurística, logística, boosting ou MLP simples disponíveis no mesmo protocolo.',
        exitCriteria: 'Baselines econômicos carregados e modelo neural demonstra valor incremental líquido contra o champion.',
        risks: 'Promover complexidade sem ganho econômico real.',
        nextStep: baselineReadiness.nextStep,
      },
    },
    {
      title: 'Passo 5 — Experimentos',
      state: activeRuns > 0 ? 'running' : trainingRuns.length > 0 ? 'done' : 'waiting',
      evidence: [
        `Treinos registrados: ${formatNumber(trainingRuns.length)}.`,
        `Trials em execução: ${formatNumber(activeRuns)}.`,
        `Falhas técnicas: ${formatNumber(failedRuns)}.`,
        `Último artefato: ${latestRun?.modelVersion ?? '—'}.`,
      ],
      interpretation: {
        objective: 'Acompanhar candidatos sem confundir trial, artefato, seed, fold e família.',
        entryCriteria: 'Há artefatos ou trials planejados para o protocolo atual.',
        exitCriteria: 'Candidatos treinados o suficiente para avaliação fora da amostra.',
        risks: 'Comparar execuções incompletas ou falhas como se fossem modelos avaliados.',
        nextStep: trainingRuns.length > 0 ? 'Abrir Treinos para investigar artefatos e métricas.' : 'Executar experimentos dentro do orçamento do protocolo.',
      },
    },
    {
      title: 'Passo 6 — Walk-forward',
      state: evaluated > 0 ? 'running' : 'waiting',
      evidence: [
        `Avaliações no leaderboard: ${formatNumber(evaluated)}.`,
        `Candidatas mantidas para pesquisa: ${formatNumber(kept)}.`,
        `Melhor challenger: ${leaderboard[0]?.modelVersion ?? '—'}.`,
      ],
      interpretation: {
        objective: 'Validar comportamento em janelas temporais fora do treino.',
        entryCriteria: 'Candidatos treinados e avaliador temporal disponível.',
        exitCriteria: 'Folds/seeds suficientes, consistência e métricas líquidas aprovadas.',
        risks: 'Usar score parcial como aprovação ou ignorar pior fold.',
        nextStep: evaluated > 0 ? 'Abrir Famílias e leaderboard para comparar famílias.' : 'Aguardar avaliações determinísticas.',
      },
    },
    {
      title: 'Passo 7 — Holdout',
      state: kept > 0 ? 'waiting' : 'blocked',
      evidence: [
        `Famílias/candidatas mantidas: ${formatNumber(kept)}.`,
        'Resultados de holdout não devem aparecer antes de autorização.',
      ],
      interpretation: {
        objective: 'Preservar período final bloqueado para decisão de governança.',
        entryCriteria: 'Protocolo congelado e gates de pesquisa aprovados.',
        exitCriteria: 'Holdout aberto uma única vez, com registro auditável.',
        risks: 'Reabrir/retunar no holdout destrói seu valor estatístico.',
        nextStep: kept > 0 ? 'Preparar checklist de prontidão; não abrir sem aprovador.' : 'Rejeitar ou repetir pesquisa antes de solicitar holdout.',
      },
    },
    {
      title: 'Passo 8 — Shadow',
      state: shadowReady ? 'waiting' : 'blocked',
      evidence: [
        shadowReady ? 'Há candidata elegível ao gate de shadow.' : 'Nenhuma candidata está elegível ao shadow.',
        'Shadow observa sinais ao vivo sem liberar ordens reais.',
      ],
      interpretation: {
        objective: 'Confirmar inferência prospectiva sem impacto operacional.',
        entryCriteria: 'Holdout/gates aprovados e monitoramento de inferência preparado.',
        exitCriteria: 'Previsões estáveis, baixa divergência e sem drift crítico.',
        risks: 'Confundir observação shadow com autorização de capital.',
        nextStep: 'Exigir banner sem capital real e registro de sinais hipotéticos.',
      },
    },
    {
      title: 'Passo 9 — Paper',
      state: paperReady ? 'waiting' : 'blocked',
      evidence: [
        paperReady ? 'Há candidata elegível ao gate de paper.' : 'Nenhuma candidata está elegível ao paper trading.',
        'Paper simula ordens, fills, custos e divergência contra backtest.',
      ],
      interpretation: {
        objective: 'Validar operação simulada antes de qualquer capital real.',
        entryCriteria: 'Shadow saudável, regras de execução e custos configurados.',
        exitCriteria: 'Dias/trades mínimos, drawdown controlado e divergência aceitável.',
        risks: 'Ignorar slippage, fills ausentes ou divergência contra backtest.',
        nextStep: 'Manter simulação até cumprir gate mínimo de dias e trades.',
      },
    },
    {
      title: 'Passo 10 — Promoção',
      state: 'blocked',
      evidence: [
        'Promoção controlada exige aprovação humana, fallback e kill switch.',
        'Estado atual da UI não indica autorização para capital real.',
      ],
      interpretation: {
        objective: 'Controlar risco antes de qualquer impacto em sinais ou capital.',
        entryCriteria: 'Paper aprovado, limites definidos, fallback ativo e aprovador identificado.',
        exitCriteria: 'Decisão registrada, monitoramento pós-promoção e rollback prontos.',
        risks: 'Ativar modelo sem autorização, limites ou trilha de auditoria.',
        nextStep: 'Manter bloqueado até conclusão de todos os gates anteriores.',
      },
    },
  ]
}

const NeuralJourneyTab: FC<NeuralJourneyTabProps> = ({
  allocation,
  allocationError,
  allocationLoading,
  leaderboard,
  leaderboardError,
  leaderboardLoading,
  quantBaselineStrategies,
  quantBaselineStrategiesError,
  quantBaselineStrategiesLoading,
  trainingRuns,
  trainingRunsError,
  trainingRunsLoading,
}) => {
  const [activeStep, setActiveStep] = useState(0)
  const steps = useMemo(
    () => buildJourneySteps(allocation, trainingRuns, leaderboard, quantBaselineStrategies),
    [allocation, trainingRuns, leaderboard, quantBaselineStrategies],
  )
  const selectedStep = steps[activeStep]
  const loading = allocationLoading || leaderboardLoading || trainingRunsLoading || quantBaselineStrategiesLoading
  const hasError = allocationError || leaderboardError || trainingRunsError || quantBaselineStrategiesError

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Redes neurais — Jornada passo a passo
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Fluxo navegável do MUEN para explicar o que já foi comprovado, o que falta e qual é o próximo passo seguro.
        </Typography>
      </Stack>

      {loading ? <Skeleton variant="rounded" height={160} /> : null}
      {hasError ? <Alert severity="warning">Alguns dados da jornada não carregaram; etapas com evidência disponível continuam visíveis.</Alert> : null}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1.25fr) minmax(320px, 0.75fr)' }, gap: 2 }}>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stepper activeStep={activeStep} orientation="vertical" nonLinear>
            {steps.map((step, index) => {
              const meta = stateMeta[step.state]
              const Icon = meta.icon
              return (
                <Step key={step.title} expanded={activeStep === index || step.state === 'running'}>
                  <StepLabel
                    icon={<Icon color={meta.color} />}
                    optional={<Chip size="small" color={meta.color} label={meta.label} variant={step.state === 'done' ? 'filled' : 'outlined'} />}
                    onClick={() => setActiveStep(index)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <Typography fontWeight={800}>{step.title}</Typography>
                  </StepLabel>
                  <StepContent>
                    <Stack spacing={1.25} sx={{ pb: 2 }}>
                      {step.evidence.map((item) => (
                        <Typography key={item} variant="body2" color="text.secondary">• {item}</Typography>
                      ))}
                      {step.blockerSummary ? (
                        <Alert severity="warning" icon={<ErrorOutlineIcon fontSize="inherit" />} sx={{ py: 0.75 }}>
                          Falta para concluir: {step.blockerSummary}.
                        </Alert>
                      ) : null}
                      <Button size="small" variant="outlined" onClick={() => setActiveStep(index)} sx={{ alignSelf: 'flex-start' }}>
                        Como interpretar
                      </Button>
                    </Stack>
                  </StepContent>
                </Step>
              )
            })}
          </Stepper>
        </Paper>

        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, alignSelf: 'start', position: { lg: 'sticky' }, top: { lg: 88 } }}>
          <Stack spacing={2}>
            <Stack spacing={0.5}>
              <Typography variant="overline" color="text.secondary">Como interpretar</Typography>
              <Typography variant="h6" fontWeight={900}>{selectedStep.title}</Typography>
              <Chip size="small" color={stateMeta[selectedStep.state].color} label={stateMeta[selectedStep.state].label} sx={{ alignSelf: 'flex-start' }} />
            </Stack>
            {selectedStep.visualChecklist ? (
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 1 }}>
                {selectedStep.visualChecklist.map((item) => (
                  <Box
                    key={item.label}
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: 'auto 1fr',
                      gap: 1,
                      p: 1.25,
                      border: '1px solid',
                      borderColor: item.ready ? 'success.light' : 'warning.light',
                      borderRadius: 2,
                      bgcolor: item.ready ? 'rgba(46, 125, 50, 0.08)' : 'rgba(237, 108, 2, 0.08)',
                    }}
                  >
                    {item.ready ? <CheckCircleIcon color="success" fontSize="small" /> : <ErrorOutlineIcon color="warning" fontSize="small" />}
                    <Box>
                      <Typography variant="subtitle2" fontWeight={900}>{item.label}</Typography>
                      <Typography variant="caption" color="text.secondary">{item.detail}</Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            ) : null}
            <Stack spacing={1.25}>
              <Box>
                <Typography variant="subtitle2" fontWeight={800}>Objetivo</Typography>
                <Typography variant="body2" color="text.secondary">{selectedStep.interpretation.objective}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={800}>Critério de entrada</Typography>
                <Typography variant="body2" color="text.secondary">{selectedStep.interpretation.entryCriteria}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={800}>Critério de saída</Typography>
                <Typography variant="body2" color="text.secondary">{selectedStep.interpretation.exitCriteria}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={800}>Riscos</Typography>
                <Typography variant="body2" color="text.secondary">{selectedStep.interpretation.risks}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={800}>Próximo passo possível</Typography>
                <Typography variant="body2" color="text.secondary">{selectedStep.interpretation.nextStep}</Typography>
              </Box>
            </Stack>
          </Stack>
        </Paper>
      </Box>
    </Stack>
  )
}

export default NeuralJourneyTab
