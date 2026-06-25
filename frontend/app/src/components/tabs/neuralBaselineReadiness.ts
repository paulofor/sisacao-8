import type {
  NeuralEvolutionLeaderboardEntry,
  NeuralTrainingRun,
  QuantBaselineStrategy,
} from '../../api/ops'

export type NeuralBaselineJourneyStatus = 'done' | 'running' | 'waiting' | 'blocked'

export interface NeuralBaselineReadiness {
  status: NeuralBaselineJourneyStatus
  baselineCount: number
  baselinesWithTrades: number
  baselinesWithEconomicMetrics: number
  positiveBaselines: number
  bestEconomicBaseline: QuantBaselineStrategy | undefined
  champion: NeuralTrainingRun | undefined
  bestChallenger: NeuralEvolutionLeaderboardEntry | undefined
  formalComparisonReady: boolean
  summary: string
  countLabel: string
  nextStep: string
  evidence: string[]
}

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR').format(value)
    : '—'

export const buildNeuralBaselineReadiness = (
  strategies: QuantBaselineStrategy[],
  trainingRuns: NeuralTrainingRun[],
  leaderboard: NeuralEvolutionLeaderboardEntry[],
): NeuralBaselineReadiness => {
  const baselinesWithTrades = strategies.filter((strategy) => (strategy.trades ?? 0) > 0).length
  const baselinesWithEconomicMetrics = strategies.filter(
    (strategy) => strategy.expectancyNetPct !== null || strategy.profitFactor !== null || strategy.robustnessScore !== null,
  ).length
  const positiveBaselines = strategies.filter(
    (strategy) => (strategy.expectancyNetPct ?? Number.NEGATIVE_INFINITY) > 0,
  ).length
  const bestEconomicBaseline = [...strategies]
    .filter((strategy) => strategy.expectancyNetPct !== null)
    .sort((left, right) => (right.expectancyNetPct ?? Number.NEGATIVE_INFINITY) - (left.expectancyNetPct ?? Number.NEGATIVE_INFINITY))[0]
  const champion = trainingRuns.find((run) => run.status?.toLowerCase() === 'approved')
  const bestChallenger = leaderboard[0]
  const formalComparisonReady = Boolean(bestEconomicBaseline && champion && bestChallenger)
  const status: NeuralBaselineJourneyStatus = formalComparisonReady
    ? 'done'
    : baselinesWithEconomicMetrics > 0
      ? 'running'
      : strategies.length > 0
        ? 'running'
        : 'waiting'
  const summary = formalComparisonReady
    ? 'Baseline econômico, champion e challenger disponíveis para comparação formal.'
    : baselinesWithEconomicMetrics > 0
      ? `${formatNumber(baselinesWithEconomicMetrics)} baselines com métrica econômica; falta comparação formal champion/challenger.`
      : strategies.length > 0
        ? 'Catálogo de baselines carregado; aguardando métricas econômicas completas.'
        : 'Aguardando catálogo de baselines econômicos.'
  const nextStep = formalComparisonReady
    ? 'Persistir a decisão do gate econômico antes de qualquer holdout.'
    : baselinesWithEconomicMetrics > 0
      ? 'Formalizar comparação champion/challenger por fold, seed e gate econômico no backend.'
      : 'Completar métricas econômicas dos baselines para destravar a comparação champion/challenger.'

  return {
    status,
    baselineCount: strategies.length,
    baselinesWithTrades,
    baselinesWithEconomicMetrics,
    positiveBaselines,
    bestEconomicBaseline,
    champion,
    bestChallenger,
    formalComparisonReady,
    summary,
    countLabel: `${formatNumber(strategies.length)} regras · ${formatNumber(baselinesWithTrades)} com trades`,
    nextStep,
    evidence: [
      `Baselines econômicos no catálogo: ${formatNumber(strategies.length)}.`,
      `Baselines com trades: ${formatNumber(baselinesWithTrades)} · com métrica econômica: ${formatNumber(baselinesWithEconomicMetrics)}.`,
      `Expectancy positiva: ${formatNumber(positiveBaselines)} · líder atual: ${bestEconomicBaseline?.strategyId ?? '—'}.`,
      `Champion aprovado: ${champion?.modelVersion ?? '—'} · challenger líder: ${bestChallenger?.modelVersion ?? '—'}.`,
      formalComparisonReady
        ? 'Comparação formal pode ser persistida pelo gate econômico.'
        : 'Comparação formal champion/challenger ainda não está persistida; não promover.',
    ],
  }
}
