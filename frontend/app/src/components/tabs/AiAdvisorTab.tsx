import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import { useMemo, useState, type FC } from 'react'

import type { AiAdvisorResponse, NeuralEvolutionLeaderboardEntry } from '../../api/ops'
import { useAiAdvisorRecommendations } from '../../hooks/useAiAdvisorRecommendations'

interface AiAdvisorTabProps {
  leaderboard: NeuralEvolutionLeaderboardEntry[]
}

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm:ss') : value
}

const formatJson = (value: unknown) => {
  if (!value || (typeof value === 'object' && Object.keys(value).length === 0)) return '—'
  return JSON.stringify(value, null, 2)
}

const buildRequest = (objective: string, maxTrials: number, leaderboard: NeuralEvolutionLeaderboardEntry[]) => ({
  advisorRunId: `frontend-gemini-${dayjs().format('YYYYMMDD-HHmmss')}`,
  task: 'propose_neural_eod_candidate_configs',
  context: {
    objective,
    currentLeaderboard: leaderboard.slice(0, 10).map((entry) => ({
      modelId: entry.modelId,
      modelVersion: entry.modelVersion,
      decision: entry.decision,
      scoreTotal: entry.scoreTotal,
      scoreDirectionalPrecision: entry.scoreDirectionalPrecision,
      scoreCoverage: entry.scoreCoverage,
      scoreGeneralization: entry.scoreGeneralization,
      scoreStability: entry.scoreStability,
      hyperparameters: entry.hyperparametersJson,
      createdAt: entry.createdAt,
    })),
  },
  constraints: {
    maxTrials,
    candidateSource: 'gemini',
    allowedModelFamilies: ['mlp', 'tabular_mlp'],
    requireLocalValidation: true,
    noRawMarketData: true,
  },
  expectedResponseSchema: {
    type: 'object',
    required: ['rationale', 'candidates'],
    properties: {
      rationale: { type: 'string' },
      candidates: {
        type: 'array',
        items: {
          type: 'object',
          required: ['architecture', 'hyperparameters'],
          properties: {
            architecture: { type: 'object' },
            hyperparameters: { type: 'object' },
            metadata: { type: 'object' },
          },
        },
      },
    },
  },
  guardrails: [
    'return_json_only',
    'do_not_promote_models',
    'do_not_use_credentials_or_raw_market_data',
    'recommendations_are_advisory_until_local_backtest',
  ],
})

const ResponseSummary: FC<{ response: AiAdvisorResponse }> = ({ response }) => (
  <Stack spacing={2}>
    <Stack direction="row" flexWrap="wrap" gap={2}>
      <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 180 }}>
        <Typography variant="overline" color="text.secondary">Provider</Typography>
        <Typography variant="h6" fontWeight={800}>{response.provider || '—'}</Typography>
      </Paper>
      <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 180 }}>
        <Typography variant="overline" color="text.secondary">Modelo</Typography>
        <Typography variant="h6" fontWeight={800}>{response.model || '—'}</Typography>
      </Paper>
      <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 180 }}>
        <Typography variant="overline" color="text.secondary">Status</Typography>
        <Box sx={{ mt: 0.5 }}><Chip label={response.status || '—'} color={response.status === 'accepted' ? 'success' : 'default'} /></Box>
      </Paper>
      <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2, minWidth: 180 }}>
        <Typography variant="overline" color="text.secondary">Criado em</Typography>
        <Typography variant="body2" fontWeight={800}>{formatDateTime(response.createdAt)}</Typography>
      </Paper>
    </Stack>

    <Alert severity="info">{response.rationale || 'Resposta sem justificativa textual.'}</Alert>

    {response.rejectionReasons.length > 0 ? (
      <Alert severity="warning">Rejeições: {response.rejectionReasons.join(', ')}</Alert>
    ) : null}

    <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
      <Table size="small" aria-label="Candidatos sugeridos pelo advisor IA">
        <TableHead>
          <TableRow>
            <TableCell>Candidato</TableCell>
            <TableCell>Arquitetura</TableCell>
            <TableCell>Hiperparâmetros</TableCell>
            <TableCell>Metadados</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {response.candidates.map((candidate, index) => (
            <TableRow key={`${candidate.candidateId}-${index}`} hover>
              <TableCell>{candidate.candidateId || `candidate-${index + 1}`}</TableCell>
              <TableCell><Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>{formatJson(candidate.architecture)}</Typography></TableCell>
              <TableCell><Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>{formatJson(candidate.hyperparameters)}</Typography></TableCell>
              <TableCell><Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>{formatJson(candidate.metadata)}</Typography></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Stack>
)

const AiAdvisorTab: FC<AiAdvisorTabProps> = ({ leaderboard }) => {
  const [objective, setObjective] = useState('Melhorar precisão direcional e generalização das redes EOD sem aumentar risco operacional.')
  const [maxTrials, setMaxTrials] = useState(3)
  const advisorMutation = useAiAdvisorRecommendations()

  const preview = useMemo(() => buildRequest(objective, maxTrials, leaderboard), [leaderboard, maxTrials, objective])

  const handleSubmit = () => {
    advisorMutation.mutate(preview)
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">Advisor IA — Gemini para redes neurais</Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhe e acione o módulo publicado de IA consultiva para sugerir melhorias nas redes neurais.
          As respostas são apenas recomendações: promoção de modelos continua bloqueada até validação local, backtest e governança.
        </Typography>
      </Stack>

      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Stack spacing={2}>
          <TextField label="Objetivo da rodada" value={objective} onChange={(event) => setObjective(event.target.value)} multiline minRows={3} fullWidth />
          <TextField label="Máximo de candidatos" type="number" value={maxTrials} onChange={(event) => setMaxTrials(Math.max(1, Number(event.target.value) || 1))} inputProps={{ min: 1, max: 10 }} sx={{ maxWidth: 220 }} />
          <Stack direction="row" gap={2} alignItems="center" flexWrap="wrap">
            <Button variant="contained" startIcon={<AutoAwesomeIcon />} onClick={handleSubmit} disabled={advisorMutation.isPending || objective.trim().length === 0}>
              Consultar Gemini
            </Button>
            <Typography variant="body2" color="text.secondary">
              Contexto enviado: top {Math.min(leaderboard.length, 10)} candidatos do leaderboard neural.
            </Typography>
          </Stack>
        </Stack>
      </Paper>

      {advisorMutation.isError ? <Alert severity="error">Erro ao consultar o advisor IA: {advisorMutation.error.message}</Alert> : null}
      {advisorMutation.isPending ? <Alert severity="info">Consultando o módulo IA publicado...</Alert> : null}
      {advisorMutation.data ? <ResponseSummary response={advisorMutation.data} /> : null}
    </Stack>
  )
}

export default AiAdvisorTab
