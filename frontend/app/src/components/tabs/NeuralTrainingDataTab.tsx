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

import type { NeuralTrainingDataAllocation } from '../../api/ops'

interface NeuralTrainingDataTabProps {
  allocation: NeuralTrainingDataAllocation[]
  allocationError?: Error | null
  allocationLoading: boolean
}

const formatNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR').format(value)
    : '—'

const formatPct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('pt-BR', {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value)
    : '—'

const formatDate = (value: string | null | undefined) => {
  if (!value) return '—'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const splitLabel = (split: string | null) => {
  if (!split) return 'Embargo/sem alocação'
  const normalized = split.toLowerCase()
  if (normalized === 'train') return 'Treino'
  if (normalized === 'validation') return 'Validação'
  if (normalized === 'test') return 'Teste'
  return split
}

const splitColor = (split: string | null) => {
  const normalized = split?.toLowerCase()
  if (normalized === 'train') return 'primary'
  if (normalized === 'validation') return 'warning'
  if (normalized === 'test') return 'success'
  return 'default'
}

const sumRows = (rows: NeuralTrainingDataAllocation[]) => {
  return rows.reduce(
    (totals, row) => ({
      rowsCount: totals.rowsCount + row.rowsCount,
      tickersCount: Math.max(totals.tickersCount, row.tickersCount),
      upCount: totals.upCount + row.upCount,
      downCount: totals.downCount + row.downCount,
      neutralCount: totals.neutralCount + row.neutralCount,
      missingOhlcvCount: totals.missingOhlcvCount + row.missingOhlcvCount,
      zeroVolumeCount: totals.zeroVolumeCount + row.zeroVolumeCount,
      suspiciousCandleCount:
        totals.suspiciousCandleCount + row.suspiciousCandleCount,
      targetHitCount: totals.targetHitCount + row.targetHitCount,
      stopHitCount: totals.stopHitCount + row.stopHitCount,
    }),
    {
      rowsCount: 0,
      tickersCount: 0,
      upCount: 0,
      downCount: 0,
      neutralCount: 0,
      missingOhlcvCount: 0,
      zeroVolumeCount: 0,
      suspiciousCandleCount: 0,
      targetHitCount: 0,
      stopHitCount: 0,
    },
  )
}

const SummaryCard: FC<{ title: string; value: string; helper?: string }> = ({
  title,
  value,
  helper,
}) => (
  <Paper
    elevation={0}
    sx={{
      p: 2.5,
      border: '1px solid',
      borderColor: 'divider',
      borderRadius: 2,
      flex: 1,
      minWidth: 220,
    }}
  >
    <Stack spacing={0.75}>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
      <Typography variant="h5" fontWeight={800}>
        {value}
      </Typography>
      {helper ? (
        <Typography variant="caption" color="text.secondary">
          {helper}
        </Typography>
      ) : null}
    </Stack>
  </Paper>
)

const AllocationBar: FC<{ row: NeuralTrainingDataAllocation; totalRows: number }> = ({
  row,
  totalRows,
}) => {
  const allocationPct = totalRows > 0 ? row.rowsCount / totalRows : 0
  return (
    <Stack spacing={0.75}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Chip
          size="small"
          label={splitLabel(row.datasetSplit)}
          color={splitColor(row.datasetSplit)}
        />
        <Typography variant="body2" color="text.secondary">
          {formatPct(allocationPct)} · {formatNumber(row.rowsCount)} linhas
        </Typography>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={Math.min(allocationPct * 100, 100)}
        sx={{ height: 10, borderRadius: 999 }}
      />
    </Stack>
  )
}

const NeuralTrainingDataTab: FC<NeuralTrainingDataTabProps> = ({
  allocation,
  allocationError,
  allocationLoading,
}) => {
  const totals = sumRows(allocation)
  const firstDate = allocation
    .map((row) => row.minReferenceDate)
    .filter(Boolean)
    .sort()[0]
  const lastDate = allocation
    .map((row) => row.maxReferenceDate)
    .filter(Boolean)
    .sort()
    .at(-1)
  const latestFeatureVersion = allocation[0]?.featureVersion ?? '—'
  const latestLabelVersion = allocation[0]?.labelVersion ?? '—'
  const qualityIssues =
    totals.missingOhlcvCount + totals.zeroVolumeCount + totals.suspiciousCandleCount

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Redes neurais — Dados de treino
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhe a alocação cronológica do dataset neural EOD entre treino,
          validação, teste e períodos de embargo, antes da promoção de modelos.
        </Typography>
      </Stack>

      {allocationLoading ? <Skeleton variant="rounded" height={150} /> : null}
      {allocationError ? (
        <Alert severity="error">
          Erro ao carregar a alocação dos dados de treino neurais.
        </Alert>
      ) : null}
      {!allocationLoading && !allocationError && allocation.length === 0 ? (
        <Alert severity="info">
          Ainda não há alocação de dataset neural materializada para exibição.
        </Alert>
      ) : null}

      {allocation.length > 0 ? (
        <>
          <Stack direction="row" flexWrap="wrap" gap={2}>
            <SummaryCard
              title="Linhas supervisionadas"
              value={formatNumber(totals.rowsCount)}
              helper={`${formatNumber(totals.tickersCount)} tickers no dataset`}
            />
            <SummaryCard
              title="Janela histórica"
              value={`${formatDate(firstDate)} — ${formatDate(lastDate)}`}
              helper="Referências usadas para treino/validação/teste"
            />
            <SummaryCard
              title="Contrato de features"
              value={latestFeatureVersion}
              helper={`Labels: ${latestLabelVersion}`}
            />
            <SummaryCard
              title="Distribuição direcional"
              value={`${formatPct(totals.upCount / totals.rowsCount)} alta`}
              helper={`${formatNumber(totals.downCount)} queda · ${formatNumber(
                totals.neutralCount,
              )} neutro`}
            />
            <SummaryCard
              title="Alvos atingidos"
              value={formatNumber(totals.targetHitCount)}
              helper={`${formatPct(
                totals.targetHitCount / totals.rowsCount,
              )} das linhas com alvo em BUY ou SELL`}
            />
            <SummaryCard
              title="Stops atingidos"
              value={formatNumber(totals.stopHitCount)}
              helper={`${formatPct(
                totals.stopHitCount / totals.rowsCount,
              )} das linhas com stop em BUY ou SELL`}
            />
            <SummaryCard
              title="Flags de qualidade"
              value={formatNumber(qualityIssues)}
              helper="OHLCV ausente, volume zero ou candle suspeito"
            />
          </Stack>

          <Paper
            elevation={0}
            sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
          >
            <Stack spacing={2}>
              <Box>
                <Typography variant="h5" fontWeight={700}>
                  Alocação dos dados por split temporal
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  A separação deve respeitar ordem cronológica e manter embargo
                  entre partições para reduzir vazamento temporal.
                </Typography>
              </Box>
              <Stack spacing={2}>
                {allocation.map((row) => (
                  <AllocationBar
                    key={`${row.featureVersion}-${row.labelVersion}-${row.datasetSplit ?? 'embargo'}`}
                    row={row}
                    totalRows={totals.rowsCount}
                  />
                ))}
              </Stack>
            </Stack>
          </Paper>

          <Paper
            elevation={0}
            sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
          >
            <Stack spacing={2}>
              <Typography variant="h5" fontWeight={700}>
                Detalhamento por split e classe
              </Typography>
              <TableContainer sx={{ maxHeight: 460 }}>
                <Table stickyHeader size="small" aria-label="Alocação neural por split">
                  <TableHead>
                    <TableRow>
                      <TableCell>Split</TableCell>
                      <TableCell>Período</TableCell>
                      <TableCell align="right">Linhas</TableCell>
                      <TableCell align="right">Tickers</TableCell>
                      <TableCell align="right">Alta</TableCell>
                      <TableCell align="right">Queda</TableCell>
                      <TableCell align="right">Neutro</TableCell>
                      <TableCell align="right">Alvo</TableCell>
                      <TableCell align="right">Stop</TableCell>
                      <TableCell align="right">Flags DQ</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {allocation.map((row) => {
                      const rowQualityIssues =
                        row.missingOhlcvCount +
                        row.zeroVolumeCount +
                        row.suspiciousCandleCount
                      return (
                        <TableRow
                          key={`${row.featureVersion}-${row.labelVersion}-${row.datasetSplit ?? 'empty'}`}
                          hover
                        >
                          <TableCell>
                            <Chip
                              size="small"
                              label={splitLabel(row.datasetSplit)}
                              color={splitColor(row.datasetSplit)}
                            />
                          </TableCell>
                          <TableCell>
                            {formatDate(row.minReferenceDate)} —{' '}
                            {formatDate(row.maxReferenceDate)}
                          </TableCell>
                          <TableCell align="right">{formatNumber(row.rowsCount)}</TableCell>
                          <TableCell align="right">{formatNumber(row.tickersCount)}</TableCell>
                          <TableCell align="right">
                            {formatNumber(row.upCount)} ({formatPct(row.upRatio)})
                          </TableCell>
                          <TableCell align="right">
                            {formatNumber(row.downCount)} ({formatPct(row.downRatio)})
                          </TableCell>
                          <TableCell align="right">
                            {formatNumber(row.neutralCount)} ({formatPct(row.neutralRatio)})
                          </TableCell>
                          <TableCell align="right">
                            {`${formatNumber(row.targetHitCount)} (${formatPct(
                              row.targetHitCount / row.rowsCount,
                            )})`}
                          </TableCell>
                          <TableCell align="right">
                            {`${formatNumber(row.stopHitCount)} (${formatPct(
                              row.stopHitCount / row.rowsCount,
                            )})`}
                          </TableCell>
                          <TableCell align="right">
                            {formatNumber(rowQualityIssues)}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </Stack>
          </Paper>
        </>
      ) : null}
    </Stack>
  )
}

export default NeuralTrainingDataTab
