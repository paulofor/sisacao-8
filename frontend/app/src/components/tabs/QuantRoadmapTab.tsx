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

import type { QuantBaselineStrategy, QuantRankingDailyEntry, QuantRankingPerformance, QuantStrategyDetailAlert } from '../../api/ops'

export type QuantRoadmapKey =
  | 'baseline'
  | 'ranking'
  | 'regime'
  | 'robustez'
  | 'paper'
  | 'comite'

interface RoadmapItem {
  key: QuantRoadmapKey
  title: string
  phase: string
  status: 'Planejada' | 'Backend pendente' | 'Frontend pendente' | 'Com dados'
  goal: string
  dataNeeds: string[]
  screenPlan: string[]
  implementationSteps: string[]
}

interface QuantRoadmapTabProps {
  selectedKey: QuantRoadmapKey
  baselineStrategies: QuantBaselineStrategy[]
  baselineStrategiesLoading: boolean
  baselineStrategiesError?: Error | null
  baselineAlerts: QuantStrategyDetailAlert[]
  baselineAlertsLoading: boolean
  baselineAlertsError?: Error | null
  rankingDaily: QuantRankingDailyEntry[]
  rankingDailyLoading: boolean
  rankingDailyError?: Error | null
  rankingPerformance: QuantRankingPerformance[]
  rankingPerformanceLoading: boolean
  rankingPerformanceError?: Error | null
}

const quantRoadmapItems: RoadmapItem[] = [
  {
    key: 'baseline',
    title: 'Estratégias Baseline e Detalhe da Estratégia',
    phase: 'Fase 2',
    status: 'Com dados',
    goal: 'Acompanhar famílias simples de estratégias e abrir o detalhe de cada hipótese, regra, parâmetro e métrica.',
    dataNeeds: ['strategy_registry', 'strategy_parameters', 'strategy_backtest_metrics', 'strategy_backtest_trades'],
    screenPlan: [
      'Cards por família com status: não iniciada, em teste, reprovada, promissora ou candidata a validação.',
      'Mini curva de capital, trades, expectancy líquida, profit factor, drawdown e estabilidade mensal.',
      'Tela de detalhe com hipótese, regras de entrada/saída, parâmetros e métricas por ticker, mês e regime.',
    ],
    implementationSteps: [
      'Consumir /ops/quant/strategies e /ops/quant/strategies/alerts.',
      'Exibir cards, tabela de estratégias e alertas calculados das views da Fase 2.',
      'Evoluir para tela de detalhe completa por strategyId quando houver sinais e métricas materializados.',
    ],
  },
  {
    key: 'ranking',
    title: 'Ranking Diário de Oportunidades e Performance do Ranking',
    phase: 'Fase 3',
    status: 'Com dados',
    goal: 'Visualizar ativos ranqueados, fatores do score e comprovar se scores maiores performam melhor historicamente.',
    dataNeeds: ['strategy_signals', 'asset_rankings', 'ranking_performance_by_decile'],
    screenPlan: [
      'Tabela com posição, ticker, score final, fatores, preço atual, liquidez, risco estimado e sugestão operacional.',
      'Cards de regime atual, volatilidade do índice, ativos em tendência e amplitude do mercado.',
      'Performance histórica de top 3, top 5 e top 10 contra seleção aleatória e Ibovespa.',
    ],
    implementationSteps: [
      'Criar views BigQuery para ranking diário e performance por decil/top N.',
      'Expor endpoints /ops/quant/ranking/daily e /ops/quant/ranking/performance.',
      'Criar tela com tabela ranqueada, decomposição de score e abas de performance.',
    ],
  },
  {
    key: 'regime',
    title: 'Regime de Mercado e Exposição Recomendada',
    phase: 'Fase 4',
    status: 'Backend pendente',
    goal: 'Mostrar quando operar, reduzir mão, bloquear compras/vendas ou ficar fora com base no regime.',
    dataNeeds: ['market_regime_daily', 'exposure_recommendations', 'strategy_performance_by_regime'],
    screenPlan: [
      'Card de regime atual com histórico por data e indicadores de tendência, volatilidade, amplitude e volume.',
      'Gráfico de performance das estratégias por regime.',
      'Painel de exposição máxima, quantidade de operações, risco por trade e limite de perda diária.',
    ],
    implementationSteps: [
      'Materializar classificação diária de regime e recomendações de exposição.',
      'Expor endpoints /ops/quant/market-regime e /ops/quant/exposure.',
      'Criar componentes de cards, timeline de regimes e painel de limites operacionais.',
    ],
  },
  {
    key: 'robustez',
    title: 'Validação Estatística e Robustez',
    phase: 'Fase 5',
    status: 'Backend pendente',
    goal: 'Separar estratégias ajustadas ao passado daquelas com estabilidade fora da amostra.',
    dataNeeds: ['strategy_validation_runs', 'walk_forward_results', 'parameter_sensitivity', 'cost_stress_tests'],
    screenPlan: [
      'Cards de treino, validação, teste, degradação fora da amostra e score de robustez.',
      'Gráfico de walk-forward e heatmap de sensibilidade de parâmetros.',
      'Painel de custos normal/estressado, slippage estressado e alertas de overfitting.',
    ],
    implementationSteps: [
      'Persistir resultados de validação, walk-forward, sensibilidade e custos estressados.',
      'Criar endpoints /ops/quant/robustness e /ops/quant/robustness/{strategyId}.',
      'Implementar filtros por estratégia, versão e janela de validação.',
    ],
  },
  {
    key: 'paper',
    title: 'Paper Trading e Diário Operacional',
    phase: 'Fase 6',
    status: 'Backend pendente',
    goal: 'Acompanhar sinais simulados em tempo quase real, entradas, saídas e divergências frente ao backtest.',
    dataNeeds: ['paper_trading_orders', 'paper_trading_events', 'paper_trading_daily_pnl'],
    screenPlan: [
      'Operações abertas, encerradas do dia, PnL diário/acumulado e aderência ao backtest.',
      'Lista de eventos: sinal gerado, sinal filtrado, entrada simulada, stop, target, expire e alerta de risco.',
      'Campo para observações manuais e exportação para análise posterior.',
    ],
    implementationSteps: [
      'Criar modelo operacional de ordens/eventos simulados.',
      'Expor endpoints /ops/quant/paper-trading e /ops/quant/operational-diary.',
      'Criar telas com atualização frequente e formulário de observações manuais.',
    ],
  },
  {
    key: 'comite',
    title: 'Comitê de Estratégias, Risco e Limites',
    phase: 'Fase 7',
    status: 'Backend pendente',
    goal: 'Controlar aprovação, pausa, reprovação e limites antes de qualquer operação real controlada.',
    dataNeeds: ['strategy_approval_checklist', 'risk_limits', 'risk_exposure_snapshots'],
    screenPlan: [
      'Lista de estratégias candidatas com status: pesquisa, validação, paper trading, piloto, reprovada ou pausada.',
      'Checklist de critérios: amostra mínima, expectativa positiva, drawdown, validação, paper trading e risco aprovado.',
      'Exposição por estratégia/ticker, risco máximo do dia, perda acumulada, limites violados e alertas de desligamento.',
    ],
    implementationSteps: [
      'Definir tabela de checklist, decisões manuais e limites de risco auditáveis.',
      'Expor endpoints /ops/quant/committee e /ops/quant/risk-limits.',
      'Criar ações protegidas para aprovar, pausar ou reprovar estratégias.',
    ],
  },
]

const statusColor = (status: RoadmapItem['status'] | string) => {
  const normalized = status.toLowerCase()
  if (normalized === 'com dados' || normalized === 'promissora') return 'success'
  if (normalized === 'planejada' || normalized === 'em_teste') return 'info'
  if (normalized === 'reprovada' || normalized === 'sem_sinais') return 'error'
  return 'warning'
}

const listSx = { margin: 0, paddingLeft: 3 }

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('pt-BR').format(value) : '—'

const formatPct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 2 }).format(value)
    : '—'

const formatDecimal = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)
    : '—'

const formatDate = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const normalizeLabel = (value: string | null | undefined) => value?.replaceAll('_', ' ') ?? '—'

const MetricCard: FC<{ title: string; value: string; helper?: string }> = ({ title, value, helper }) => (
  <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, flex: 1, minWidth: 190 }}>
    <Stack spacing={0.75}>
      <Typography variant="overline" color="text.secondary">{title}</Typography>
      <Typography variant="h5" fontWeight={800}>{value}</Typography>
      {helper ? <Typography variant="caption" color="text.secondary">{helper}</Typography> : null}
    </Stack>
  </Paper>
)

const BaselineStrategiesScreen: FC<{
  strategies: QuantBaselineStrategy[]
  loading: boolean
  error?: Error | null
  alerts: QuantStrategyDetailAlert[]
  alertsLoading: boolean
  alertsError?: Error | null
}> = ({ strategies, loading, error, alerts, alertsLoading, alertsError }) => {
  const totalSignals = strategies.reduce((total, strategy) => total + strategy.generatedSignals, 0)
  const totalTrades = strategies.reduce((total, strategy) => total + (strategy.trades ?? 0), 0)
  const promisingCount = strategies.filter((strategy) => strategy.computedStatus === 'promissora').length
  const strategiesWithAlerts = alerts.filter((item) => item.alerts.length > 0).length

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" color="text.primary" fontWeight={800}>Estratégias Baseline</Typography>
        <Typography variant="body1" color="text.secondary">
          Dados operacionais da Fase 2 vindos das views de status e alertas. Use esta tela para saber se já existem sinais,
          trades e métricas suficientes para sair do roadmap e avançar para validação.
        </Typography>
      </Stack>

      {error ? <Alert severity="error">Erro ao carregar estratégias baseline pelo backend.</Alert> : null}
      {alertsError ? <Alert severity="error">Erro ao carregar alertas de detalhe das estratégias.</Alert> : null}
      {loading ? <Skeleton variant="rounded" height={160} /> : null}

      {!loading && !error ? (
        <Stack direction="row" flexWrap="wrap" gap={2}>
          <MetricCard title="Famílias baseline" value={formatNumber(strategies.length)} helper="Registros na view de status" />
          <MetricCard title="Sinais gerados" value={formatNumber(totalSignals)} helper="Candidatos da Fase 2" />
          <MetricCard title="Trades simulados" value={formatNumber(totalTrades)} helper="Motor comum de backtest" />
          <MetricCard title="Promissoras" value={formatNumber(promisingCount)} helper="Status calculado" />
          <MetricCard title="Com alertas" value={formatNumber(strategiesWithAlerts)} helper="Detalhe da estratégia" />
        </Stack>
      ) : null}

      {!loading && !error && strategies.length === 0 ? (
        <Alert severity="warning">Nenhuma estratégia baseline retornada pelo endpoint /ops/quant/strategies.</Alert>
      ) : null}

      {!loading && !error && strategies.length > 0 && totalSignals === 0 ? (
        <Alert severity="info">
          As baselines já aparecem no catálogo, mas a view de candidatos ainda não gerou sinais. A tela fica pronta para dados
          assim que houver candidatos materializados e o backtest comum popular as métricas.
        </Alert>
      ) : null}

      {!loading && !error && strategies.length > 0 ? (
        <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h5" fontWeight={800}>Status por família de estratégia</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
              {strategies.map((strategy) => (
                <Paper key={strategy.strategyId} elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                  <Stack spacing={1.25}>
                    <Stack direction="row" gap={1} flexWrap="wrap">
                      <Chip size="small" color={statusColor(strategy.computedStatus ?? '')} label={normalizeLabel(strategy.computedStatus)} />
                      <Chip size="small" variant="outlined" label={strategy.strategyVersion} />
                    </Stack>
                    <Typography variant="subtitle1" fontWeight={800}>{normalizeLabel(strategy.strategyFamily)}</Typography>
                    <Typography variant="body2" color="text.secondary">{strategy.hypothesis ?? 'Sem hipótese cadastrada.'}</Typography>
                    <Stack spacing={0.75}>
                      <Typography variant="caption" color="text.secondary">Sinais: <strong>{formatNumber(strategy.generatedSignals)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary">Trades: <strong>{formatNumber(strategy.trades)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary">Último sinal: <strong>{formatDate(strategy.lastSignalDate)}</strong></Typography>
                    </Stack>
                  </Stack>
                </Paper>
              ))}
            </Box>
          </Stack>
        </Paper>
      ) : null}

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h5" fontWeight={800}>Métricas e alertas</Typography>
          {alertsLoading ? <LinearProgress /> : null}
          {!loading && !error && strategies.length > 0 ? (
            <TableContainer sx={{ maxHeight: 520 }}>
              <Table stickyHeader size="small" aria-label="Estratégias baseline">
                <TableHead>
                  <TableRow>
                    <TableCell>Estratégia</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Sinais</TableCell>
                    <TableCell align="right">Dias</TableCell>
                    <TableCell align="right">Trades</TableCell>
                    <TableCell align="right">Expectancy</TableCell>
                    <TableCell align="right">Profit factor</TableCell>
                    <TableCell align="right">Drawdown</TableCell>
                    <TableCell>Alertas</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {strategies.map((strategy) => {
                    const strategyAlerts = alerts.find((item) => item.strategyId === strategy.strategyId)?.alerts ?? []
                    return (
                      <TableRow key={`${strategy.strategyId}-row`} hover>
                        <TableCell>
                          <Typography fontWeight={800}>{strategy.strategyId}</Typography>
                          <Typography variant="caption" color="text.secondary">{normalizeLabel(strategy.strategyFamily)}</Typography>
                        </TableCell>
                        <TableCell><Chip size="small" color={statusColor(strategy.computedStatus ?? '')} label={normalizeLabel(strategy.computedStatus)} /></TableCell>
                        <TableCell align="right">{formatNumber(strategy.generatedSignals)}</TableCell>
                        <TableCell align="right">{formatNumber(strategy.signalDays)}</TableCell>
                        <TableCell align="right">{formatNumber(strategy.trades)}</TableCell>
                        <TableCell align="right">{formatPct(strategy.expectancyNetPct)}</TableCell>
                        <TableCell align="right">{formatDecimal(strategy.profitFactor)}</TableCell>
                        <TableCell align="right">{formatPct(strategy.maxDrawdownPct)}</TableCell>
                        <TableCell>
                          {strategyAlerts.length > 0 ? (
                            <Stack direction="row" gap={0.5} flexWrap="wrap">
                              {strategyAlerts.map((alert) => <Chip key={alert} size="small" color="warning" label={normalizeLabel(alert)} />)}
                            </Stack>
                          ) : '—'}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  )
}


const RankingScreen: FC<{
  daily: QuantRankingDailyEntry[]
  dailyLoading: boolean
  dailyError?: Error | null
  performance: QuantRankingPerformance[]
  performanceLoading: boolean
  performanceError?: Error | null
}> = ({ daily, dailyLoading, dailyError, performance, performanceLoading, performanceError }) => {
  const referenceDate = daily.find((item) => item.referenceDate)?.referenceDate
  const modelCount = new Set(daily.map((item) => item.rankingModelId)).size
  const operateCount = daily.filter((item) => item.actionSuggestion === 'operar').length
  const avgScore = daily.length > 0 ? daily.reduce((total, item) => total + (item.finalScore ?? 0), 0) / daily.length : null

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" color="text.primary" fontWeight={800}>Ranking Diário de Oportunidades</Typography>
        <Typography variant="body1" color="text.secondary">
          Tela operacional da Fase 3 com ativos ranqueados, decomposição de fatores e performance histórica por Top N.
        </Typography>
      </Stack>

      {dailyError ? <Alert severity="error">Erro ao carregar ranking diário pelo endpoint /ops/quant/ranking/daily.</Alert> : null}
      {performanceError ? <Alert severity="error">Erro ao carregar performance pelo endpoint /ops/quant/ranking/performance.</Alert> : null}
      {dailyLoading ? <Skeleton variant="rounded" height={160} /> : null}

      {!dailyLoading && !dailyError ? (
        <Stack direction="row" flexWrap="wrap" gap={2}>
          <MetricCard title="Data do ranking" value={formatDate(referenceDate)} helper="Última data materializada" />
          <MetricCard title="Modelos ativos" value={formatNumber(modelCount)} helper="Configurações em teste" />
          <MetricCard title="Ativos ranqueados" value={formatNumber(daily.length)} helper="Universo elegível" />
          <MetricCard title="Sugestão operar" value={formatNumber(operateCount)} helper="Score e risco favoráveis" />
          <MetricCard title="Score médio" value={formatDecimal(avgScore)} helper="Média dos registros carregados" />
        </Stack>
      ) : null}

      {!dailyLoading && !dailyError && daily.length === 0 ? (
        <Alert severity="warning">Nenhum ativo retornado pelo endpoint /ops/quant/ranking/daily. Aplique a view da Fase 3 e confirme dados diários elegíveis.</Alert>
      ) : null}

      {!dailyLoading && !dailyError && daily.length > 0 ? (
        <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h5" fontWeight={800}>Oportunidades ranqueadas</Typography>
            <TableContainer sx={{ maxHeight: 560 }}>
              <Table stickyHeader size="small" aria-label="Ranking diário de oportunidades">
                <TableHead>
                  <TableRow>
                    <TableCell>Rank</TableCell>
                    <TableCell>Ativo</TableCell>
                    <TableCell>Modelo</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell align="right">Preço</TableCell>
                    <TableCell align="right">Liquidez</TableCell>
                    <TableCell align="right">Risco</TableCell>
                    <TableCell align="right">Ret. 5d</TableCell>
                    <TableCell>Fatores</TableCell>
                    <TableCell>Sugestão</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {daily.map((item) => (
                    <TableRow key={`${item.rankingModelId}-${item.referenceDate}-${item.rankingPosition}-${item.ticker}`} hover>
                      <TableCell><Chip size="small" color={item.rankingPosition <= 5 ? 'primary' : 'default'} label={`#${item.rankingPosition}`} /></TableCell>
                      <TableCell><Typography fontWeight={800}>{item.ticker}</Typography><Typography variant="caption" color="text.secondary">Decil {item.rankingDecile}</Typography></TableCell>
                      <TableCell><Typography variant="caption">{item.rankingModelId}</Typography></TableCell>
                      <TableCell align="right">{formatDecimal(item.finalScore)}</TableCell>
                      <TableCell align="right">{formatDecimal(item.currentPrice)}</TableCell>
                      <TableCell align="right">{formatNumber(item.liquidityValue)}</TableCell>
                      <TableCell align="right">{formatPct(item.estimatedRisk)}</TableCell>
                      <TableCell align="right">{formatPct(item.forwardReturn5d)}</TableCell>
                      <TableCell>
                        <Stack direction="row" gap={0.5} flexWrap="wrap">
                          <Chip size="small" variant="outlined" label={`FR ${formatDecimal(item.relativeStrengthFactor)}`} />
                          <Chip size="small" variant="outlined" label={`Mom ${formatDecimal(item.shortMomentumFactor)}`} />
                          <Chip size="small" variant="outlined" label={`Vol ${formatDecimal(item.relativeVolumeFactor)}`} />
                        </Stack>
                      </TableCell>
                      <TableCell><Chip size="small" color={statusColor(item.actionSuggestion ?? '')} label={normalizeLabel(item.actionSuggestion)} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Stack>
        </Paper>
      ) : null}

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h5" fontWeight={800}>Performance histórica do ranking</Typography>
          {performanceLoading ? <LinearProgress /> : null}
          {!performanceLoading && performance.length === 0 ? <Alert severity="info">Sem métricas históricas por Top N/decil.</Alert> : null}
          {performance.length > 0 ? (
            <TableContainer>
              <Table size="small" aria-label="Performance histórica do ranking">
                <TableHead><TableRow><TableCell>Modelo</TableCell><TableCell align="right">Top N</TableCell><TableCell align="right">Dias</TableCell><TableCell align="right">Retorno 5d</TableCell><TableCell align="right">Excesso vs aleatório</TableCell><TableCell align="right">Taxa positiva</TableCell><TableCell align="right">Top - bottom</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
                <TableBody>{performance.map((item) => (
                  <TableRow key={`${item.rankingModelId}-${item.topN}`} hover>
                    <TableCell>{item.rankingModelId}</TableCell><TableCell align="right">{item.topN}</TableCell><TableCell align="right">{formatNumber(item.portfolioDays)}</TableCell><TableCell align="right">{formatPct(item.avgTopNReturn5d)}</TableCell><TableCell align="right">{formatPct(item.avgExcessVsRandom5d)}</TableCell><TableCell align="right">{formatPct(item.positiveDayRate)}</TableCell><TableCell align="right">{formatPct(item.topMinusBottomDecileReturn5d)}</TableCell><TableCell><Chip size="small" color={statusColor(item.rankingStatus ?? '')} label={normalizeLabel(item.rankingStatus)} /></TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  )
}

const QuantRoadmapTab: FC<QuantRoadmapTabProps> = ({
  selectedKey,
  baselineStrategies,
  baselineStrategiesLoading,
  baselineStrategiesError,
  baselineAlerts,
  baselineAlertsLoading,
  baselineAlertsError,
  rankingDaily,
  rankingDailyLoading,
  rankingDailyError,
  rankingPerformance,
  rankingPerformanceLoading,
  rankingPerformanceError,
}) => {
  const item = quantRoadmapItems.find((candidate) => candidate.key === selectedKey) ?? quantRoadmapItems[0]

  if (item.key === 'ranking') {
    return (
      <RankingScreen
        daily={rankingDaily}
        dailyLoading={rankingDailyLoading}
        dailyError={rankingDailyError}
        performance={rankingPerformance}
        performanceLoading={rankingPerformanceLoading}
        performanceError={rankingPerformanceError}
      />
    )
  }

  if (item.key === 'baseline') {
    return (
      <BaselineStrategiesScreen
        strategies={baselineStrategies}
        loading={baselineStrategiesLoading}
        error={baselineStrategiesError}
        alerts={baselineAlerts}
        alertsLoading={baselineAlertsLoading}
        alertsError={baselineAlertsError}
      />
    )
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" color="text.primary" fontWeight={800}>Plano de telas quantitativas</Typography>
        <Typography variant="body1" color="text.secondary">
          Use o menu lateral para navegar pelos submenus que ainda precisam ganhar telas completas no Sisacao-8.
        </Typography>
      </Stack>

      <Alert severity="info">
        Esta tela organiza o backlog visual: ela não substitui os endpoints definitivos, mas deixa claro o que precisa ser exposto
        no backend e implementado no frontend para cada fase do plano quantitativo.
      </Alert>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
        {quantRoadmapItems.map((roadmapItem) => {
          const isSelected = roadmapItem.key === item.key
          return (
            <Paper
              key={roadmapItem.key}
              elevation={0}
              sx={{
                p: 2,
                border: '1px solid',
                borderColor: isSelected ? 'primary.main' : 'divider',
                borderRadius: 2,
                bgcolor: isSelected ? 'action.selected' : 'background.paper',
                boxShadow: isSelected ? 'inset 4px 0 0 #0f4c81' : 'none',
              }}
            >
              <Stack spacing={1}>
                <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
                  <Chip label={roadmapItem.phase} color={isSelected ? 'primary' : 'default'} size="small" />
                  <Chip label={roadmapItem.status} color={statusColor(roadmapItem.status)} size="small" variant={isSelected ? 'filled' : 'outlined'} />
                </Stack>
                <Typography variant="subtitle1" fontWeight={800}>{roadmapItem.title}</Typography>
                <Typography variant="body2" color="text.secondary">{roadmapItem.goal}</Typography>
              </Stack>
            </Paper>
          )
        })}
      </Box>

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
            <Chip label={item.phase} color="primary" />
            <Chip label={item.status} color={statusColor(item.status)} />
          </Stack>
          <Typography variant="h5" fontWeight={800}>{item.title}</Typography>
          <Typography variant="body1" color="text.secondary">{item.goal}</Typography>

          <Stack spacing={1}>
            <Typography variant="h6">Dados necessários</Typography>
            <Box component="ul" sx={listSx}>
              {item.dataNeeds.map((need) => <li key={need}>{need}</li>)}
            </Box>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Plano da tela</Typography>
            <Box component="ul" sx={listSx}>
              {item.screenPlan.map((step) => <li key={step}>{step}</li>)}
            </Box>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Sequência de implementação</Typography>
            <Box component="ol" sx={listSx}>
              {item.implementationSteps.map((step) => <li key={step}>{step}</li>)}
            </Box>
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  )
}

export default QuantRoadmapTab
