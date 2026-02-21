import {
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { OpsPipelineJob } from '../../api/ops'
import StatusChip from '../StatusChip'

interface PipelineStatusTableProps {
  jobs: OpsPipelineJob[]
  isLoading: boolean
  error?: Error | null
}

const formatDateTime = (value: string | null) => {
  if (!value) {
    return '—'
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm') : value
}

const PipelineStatusTable: FC<PipelineStatusTableProps> = ({ jobs, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Falha ao carregar o status da pipeline. Verifique a API do backend.</Alert>
  }

  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}
    >
      <Typography variant="h6" fontWeight={600} sx={{ p: 3, pb: 0 }}>
        Execuções da Pipeline
      </Typography>
      <Table size="small" aria-label="Status das execuções da pipeline">
        <TableHead>
          <TableRow>
            <TableCell>Job</TableCell>
            <TableCell>Última execução</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Silêncio</TableCell>
            <TableCell align="right">Minutos desde</TableCell>
            <TableCell>Deadline</TableCell>
            <TableCell>Run ID</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading && jobs.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} align="center">
                <Typography variant="body2" color="text.secondary">
                  Carregando execuções...
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}

          {jobs.map((job) => (
            <TableRow key={`${job.jobName}-${job.lastRunId ?? 'na'}`} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {job.jobName}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.primary">
                  {formatDateTime(job.lastRunAt)}
                </Typography>
              </TableCell>
              <TableCell>
                <StatusChip status={job.lastStatus ?? '—'} />
              </TableCell>
              <TableCell>
                <StatusChip status={job.silent ? 'SILENT' : 'ON'} />
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" color="text.primary">
                  {job.minutesSinceLastRun}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.primary">
                  {formatDateTime(job.deadlineAt)}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {job.lastRunId ?? '—'}
                </Typography>
              </TableCell>
            </TableRow>
          ))}

          {!isLoading && jobs.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} align="center">
                <Typography variant="body2" color="text.secondary">
                  Nenhum job encontrado para o pipeline monitorado.
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </Paper>
  )
}

export default PipelineStatusTable
