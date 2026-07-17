import { Alert, Box, Chip, Paper, Skeleton, Stack, Typography } from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { NeuralEvolutionActivity } from '../../api/ops'

interface NeuralCreationActivityTabProps {
  activity: NeuralEvolutionActivity[]
  error?: Error | null
  loading: boolean
}

const strategyLabels: Record<string, string> = {
  phase3_new_families: 'Fase 3 · novas famílias',
  apolo_challenger_refinement: 'Apolo · refinamento',
  apolo_challenger_stability: 'Apolo · estabilidade',
  apolo_challenger_shadow: 'Apolo · shadow',
}

const strategyColors: Record<string, string> = {
  phase3_new_families: '#1976d2',
  apolo_challenger_refinement: '#7b1fa2',
  apolo_challenger_stability: '#00897b',
  apolo_challenger_shadow: '#ed6c02',
}

const formatStrategy = (strategy: string | null) => strategyLabels[strategy ?? ''] ?? strategy ?? 'Sem estratégia'
const strategyColor = (strategy: string | null) => strategyColors[strategy ?? ''] ?? '#607d8b'

const NeuralCreationActivityTab: FC<NeuralCreationActivityTabProps> = ({ activity, error, loading }) => {
  const ordered = [...activity].sort((left, right) => (right.activityDate ?? '').localeCompare(left.activityDate ?? ''))
  const latestDate = ordered[0]?.activityDate ?? null
  const latest = ordered.filter((item) => item.activityDate === latestDate)
  const totals = latest.reduce(
    (result, item) => ({
      runs: result.runs + item.runsCount,
      trained: result.trained + item.trainedCount,
      candidates: result.candidates + item.candidatesCount,
      failures: result.failures + item.failedRunsCount,
    }),
    { runs: 0, trained: 0, candidates: 0, failures: 0 },
  )
  const maxRuns = Math.max(1, ...ordered.map((item) => item.runsCount))
  const activityByDay = ordered.reduce<Array<{ date: string | null; entries: NeuralEvolutionActivity[] }>>(
    (groups, entry) => {
      const current = groups.at(-1)
      if (current?.date === entry.activityDate) {
        current.entries.push(entry)
      } else {
        groups.push({ date: entry.activityDate, entries: [entry] })
      }
      return groups
    },
    [],
  )

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" color="text.primary">Criação de redes</Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhamento diário das rodadas do orquestrador: criação de candidatas, treinos e decisões de gate.
        </Typography>
      </Stack>

      {loading ? <Skeleton variant="rounded" height={220} /> : null}
      {error ? <Alert severity="error">Não foi possível carregar a atividade diária de criação neural.</Alert> : null}
      {!loading && !error && ordered.length === 0 ? <Alert severity="info">Ainda não há execuções de evolução neural nos últimos 30 dias.</Alert> : null}

      {!loading && !error && ordered.length > 0 ? <>
        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6" fontWeight={800}>Resumo do último dia com atividade</Typography>
            <Typography variant="body2" color="text.secondary">
              {latestDate ? dayjs(latestDate).format('DD/MM/YYYY') : '—'} · as execuções abaixo são atualizadas automaticamente a cada minuto.
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap flexWrap="wrap">
              <Chip color="primary" label={`${totals.runs} execuções`} />
              <Chip color="success" label={`${totals.candidates} candidatas geradas`} />
              <Chip color="success" variant="outlined" label={`${totals.trained} treinadas`} />
              <Chip color={totals.failures === 0 ? 'success' : 'error'} label={`${totals.failures} falhas`} />
            </Stack>
          </Stack>
        </Paper>

        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack spacing={2}>
            <Stack spacing={0.5}>
              <Typography variant="h6" fontWeight={800}>Execuções por dia e estratégia</Typography>
              <Typography variant="body2" color="text.secondary">Dias mais recentes aparecem primeiro. Cada grupo separa visualmente as estratégias executadas naquela data.</Typography>
            </Stack>
            <Stack spacing={2}>
              {activityByDay.map((day) => {
                const dayRuns = day.entries.reduce((total, item) => total + item.runsCount, 0)
                return (
                  <Box key={day.date ?? 'unknown-date'} sx={{ border: '1px solid', borderColor: 'divider', borderLeft: '4px solid', borderLeftColor: 'primary.light', borderRadius: 2, overflow: 'hidden' }}>
                    <Box sx={{ px: 2, py: 1, bgcolor: 'action.hover', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
                      <Typography variant="subtitle2" fontWeight={800}>{day.date ? dayjs(day.date).format('DD/MM/YYYY') : 'Data indisponível'}</Typography>
                      <Chip size="small" label={`${dayRuns} execuções`} />
                    </Box>
                    <Stack spacing={1.25} sx={{ p: 2 }}>
                      {day.entries.map((item) => (
                        <Box key={`${item.activityDate}-${item.strategy}`} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 64px', sm: '1fr 145px' }, gap: 1, alignItems: 'center' }}>
                          <Box sx={{ height: 28, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden' }}>
                            <Box sx={{ width: `${Math.max(4, item.runsCount / maxRuns * 100)}%`, height: '100%', bgcolor: strategyColor(item.strategy), borderRadius: 1, display: 'flex', alignItems: 'center', px: 1, minWidth: 34 }}>
                              <Typography variant="caption" sx={{ color: 'common.white', fontWeight: 800 }}>{item.runsCount}</Typography>
                            </Box>
                          </Box>
                          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'right' }}>{formatStrategy(item.strategy)}</Typography>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )
              })}
            </Stack>
          </Stack>
        </Paper>

        <Paper elevation={0} sx={{ p: 2.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Typography variant="h6" fontWeight={800} gutterBottom>Detalhe da atividade mais recente</Typography>
          <Stack spacing={1}>
            {latest.map((item) => <Box key={item.strategy} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
              <Typography variant="body2" fontWeight={700}>{formatStrategy(item.strategy)}</Typography>
              <Typography variant="body2" color="text.secondary">{item.runsCount} runs · {item.candidatesCount} candidatas · {item.trainedCount} treinadas · {item.gateDecisionsCount} gates</Typography>
            </Box>)}
          </Stack>
        </Paper>
      </> : null}
    </Stack>
  )
}

export default NeuralCreationActivityTab
