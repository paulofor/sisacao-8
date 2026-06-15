import { Alert, Box, Chip, Paper, Stack, Typography } from '@mui/material'
import type { FC } from 'react'

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
  status: 'Planejada' | 'Backend pendente' | 'Frontend pendente'
  goal: string
  dataNeeds: string[]
  screenPlan: string[]
  implementationSteps: string[]
}

const quantRoadmapItems: RoadmapItem[] = [
  {
    key: 'baseline',
    title: 'Estratégias Baseline e Detalhe da Estratégia',
    phase: 'Fase 2',
    status: 'Backend pendente',
    goal: 'Acompanhar famílias simples de estratégias e abrir o detalhe de cada hipótese, regra, parâmetro e métrica.',
    dataNeeds: ['strategy_registry', 'strategy_parameters', 'strategy_backtest_metrics', 'strategy_backtest_trades'],
    screenPlan: [
      'Cards por família com status: não iniciada, em teste, reprovada, promissora ou candidata a validação.',
      'Mini curva de capital, trades, expectancy líquida, profit factor, drawdown e estabilidade mensal.',
      'Tela de detalhe com hipótese, regras de entrada/saída, parâmetros e métricas por ticker, mês e regime.',
    ],
    implementationSteps: [
      'Criar endpoints /ops/quant/strategies e /ops/quant/strategies/{id}.',
      'Implementar hooks TanStack Query e tipos TypeScript para estratégias.',
      'Criar grid de estratégias e navegação para detalhe usando o menu quantitativo.',
    ],
  },
  {
    key: 'ranking',
    title: 'Ranking Diário de Oportunidades e Performance do Ranking',
    phase: 'Fase 3',
    status: 'Backend pendente',
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

interface QuantRoadmapTabProps {
  selectedKey: QuantRoadmapKey
}

const statusColor = (status: RoadmapItem['status']) => (status === 'Planejada' ? 'info' : 'warning')

const listSx = { margin: 0, paddingLeft: 3 }

const QuantRoadmapTab: FC<QuantRoadmapTabProps> = ({ selectedKey }) => {
  const item = quantRoadmapItems.find((candidate) => candidate.key === selectedKey) ?? quantRoadmapItems[0]

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
