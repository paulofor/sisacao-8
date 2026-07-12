import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import {
  Alert,
  Box,
  Chip,
  LinearProgress,
  Paper,
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

import type { NeuralChampionMonitoring } from '../../api/ops'
import StatusChip from '../StatusChip'

interface NeuralChampionTabProps {
  data: NeuralChampionMonitoring | null | undefined
  isLoading: boolean
  error?: Error | null
}

const formatDate = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const formatPercent = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

const formatNumber = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('pt-BR', { maximumFractionDigits: digits })
}

const NeuralChampionTab: FC<NeuralChampionTabProps> = ({ data, isLoading, error }) => {
  const champion = data?.champion ?? null
  const fantasyName = data?.fantasyName ?? 'Apolo NEV'
  const fantasyNameOrigin = data?.fantasyNameOrigin ?? 'Apolo, deus greco-romano associado à profecia, clareza e precisão.'
  const gateDecision = data?.gateDecision ?? null
  const predictions = data?.predictions ?? []
  const signals = data?.signals ?? []
  const blockedTickers = new Set(['ONCO3', 'VVEO3', 'AMBP3'])
  const blockedPredictionCount = predictions.filter((prediction) => blockedTickers.has(prediction.ticker)).length
  const blockedSignalCount = signals.filter((signal) => blockedTickers.has(signal.ticker)).length
  const directionalPredictionCount = predictions.filter(
    (prediction) => !['HOLD', 'NEUTRAL', ''].includes((prediction.suggestedAction ?? '').toUpperCase()),
  ).length
  const latestPrediction = predictions[0] ?? null
  const showAbstentionNotice = predictions.length > 0 && signals.length === 0

  if (isLoading) {
    return <LinearProgress />
  }

  if (error) {
    return <Alert severity="error">Não foi possível carregar o acompanhamento do champion: {error.message}</Alert>
  }

  if (!champion) {
    return <Alert severity="warning">Nenhum champion neural aprovado foi encontrado no registry.</Alert>
  }

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
            <EmojiEventsIcon color="warning" />
            <Typography variant="h5" component="h2">
              {fantasyName}
            </Typography>
            <StatusChip status={champion.status ?? 'approved'} />
          </Stack>
          <Typography variant="subtitle1" color="text.secondary">
            Champion neural aprovado · {fantasyNameOrigin}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
            Nome técnico: {champion.modelVersion}
          </Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} flexWrap="wrap">
            <Chip label={`Dataset: ${champion.trainingDatasetSnapshot ?? '—'}`} />
            <Chip label={`Feature: ${champion.featureVersion}`} />
            <Chip label={`Label: ${champion.labelVersion}`} />
            <Chip label={`Criado: ${formatDateTime(champion.createdAt)}`} />
          </Stack>
        </Stack>
      </Paper>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">Gate MUEN</Typography>
          <Typography variant="h5">{gateDecision?.decisionStatus ?? '—'}</Typography>
          <Typography variant="body2" color="text.secondary">
            {gateDecision?.decisionId ?? 'Sem decisão associada'}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">Mediana delta</Typography>
          <Typography variant="h5">{formatPercent(gateDecision?.medianDeltaExpectancyVsChampion, 2)}</Typography>
          <Typography variant="body2" color="text.secondary">vs. champion anterior</Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">Folds positivos</Typography>
          <Typography variant="h5">{gateDecision?.positiveFolds ?? '—'}</Typography>
          <Typography variant="body2" color="text.secondary">seeds: {gateDecision?.seeds ?? '—'}</Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">Trades / drawdown</Typography>
          <Typography variant="h5">{gateDecision?.totalTrades ?? '—'} / {formatPercent(gateDecision?.maxDrawdown, 2)}</Typography>
          <Typography variant="body2" color="text.secondary">estável: {gateDecision?.stableAcrossSeeds ? 'sim' : 'não'}</Typography>
        </Paper>
      </Stack>

      <Alert severity={blockedPredictionCount || blockedSignalCount ? 'error' : 'success'}>
        Tickers bloqueados monitorados: ONCO3, VVEO3 e AMBP3. Predições bloqueadas encontradas: {blockedPredictionCount}; sinais bloqueados encontrados: {blockedSignalCount}.
      </Alert>

      {showAbstentionNotice ? (
        <Alert severity="info">
          Abstenção operacional do champion: há {predictions.length} predições para {formatDate(latestPrediction?.referenceDate)} válidas em {formatDate(latestPrediction?.validFor)}, mas nenhum sinal BUY/SELL foi gravado. {directionalPredictionCount === 0 ? 'Todas as predições recentes ficaram em HOLD/neutral sob os thresholds atuais.' : `${directionalPredictionCount} predição(ões) direcional(is) apareceram, mas nenhuma passou pelos filtros operacionais de sinal.`}
        </Alert>
      ) : null}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Predições mais recentes do champion</Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Data ref.</TableCell>
                <TableCell>Válido para</TableCell>
                <TableCell>Ticker</TableCell>
                <TableCell>Ação</TableCell>
                <TableCell align="right">Confiança</TableCell>
                <TableCell align="right">P(up)</TableCell>
                <TableCell align="right">P(down)</TableCell>
                <TableCell align="right">P(neutral)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {predictions.slice(0, 20).map((prediction) => (
                <TableRow key={`${prediction.referenceDate}-${prediction.ticker}`}>
                  <TableCell>{formatDate(prediction.referenceDate)}</TableCell>
                  <TableCell>{formatDate(prediction.validFor)}</TableCell>
                  <TableCell>{prediction.ticker}</TableCell>
                  <TableCell>{prediction.suggestedAction}</TableCell>
                  <TableCell align="right">{formatPercent(prediction.confidence)}</TableCell>
                  <TableCell align="right">{formatPercent(prediction.probUp)}</TableCell>
                  <TableCell align="right">{formatPercent(prediction.probDown)}</TableCell>
                  <TableCell align="right">{formatPercent(prediction.probNeutral)}</TableCell>
                </TableRow>
              ))}
              {!predictions.length ? (
                <TableRow>
                  <TableCell colSpan={8}>Ainda não há predições gravadas para o champion aprovado.</TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Sinais operacionais gerados a partir do champion</Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Data ref.</TableCell>
                <TableCell>Válido para</TableCell>
                <TableCell>Ticker</TableCell>
                <TableCell>Lado</TableCell>
                <TableCell align="right">Entrada</TableCell>
                <TableCell align="right">Alvo</TableCell>
                <TableCell align="right">Stop</TableCell>
                <TableCell align="right">Score</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {signals.map((signal) => (
                <TableRow key={`${signal.dateRef}-${signal.ticker}-${signal.side}`}>
                  <TableCell>{formatDate(signal.dateRef)}</TableCell>
                  <TableCell>{formatDate(signal.validFor)}</TableCell>
                  <TableCell>{signal.ticker}</TableCell>
                  <TableCell>{signal.side}</TableCell>
                  <TableCell align="right">{formatNumber(signal.entry)}</TableCell>
                  <TableCell align="right">{formatNumber(signal.target)}</TableCell>
                  <TableCell align="right">{formatNumber(signal.stop)}</TableCell>
                  <TableCell align="right">{formatPercent(signal.score)}</TableCell>
                </TableRow>
              ))}
              {!signals.length ? (
                <TableRow>
                  <TableCell colSpan={8}>Ainda não há sinais operacionais gravados para este champion.</TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Box>
        <Typography variant="caption" color="text.secondary">
          Atualização automática a cada 5 minutos. Este painel é apenas para acompanhamento operacional do modelo aprovado.
        </Typography>
      </Box>
    </Stack>
  )
}

export default NeuralChampionTab
