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

import type { OpsIncident } from '../../api/ops'
import StatusChip from '../StatusChip'

interface IncidentsTableProps {
  incidents: OpsIncident[]
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

const IncidentsTable: FC<IncidentsTableProps> = ({ incidents, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Não foi possível carregar os incidentes abertos.</Alert>
  }

  return (
    <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <Typography variant="h6" fontWeight={600} sx={{ p: 3, pb: 0 }}>
        Incidentes Abertos
      </Typography>
      <Table size="small" aria-label="Incidentes abertos">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Check</TableCell>
            <TableCell>Severity</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Origem</TableCell>
            <TableCell>Run ID</TableCell>
            <TableCell>Criado em</TableCell>
            <TableCell>Resumo</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading && incidents.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} align="center">
                <Typography variant="body2" color="text.secondary">
                  Carregando incidentes...
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}

          {incidents.map((incident) => (
            <TableRow key={incident.incidentId} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {incident.incidentId}
                </Typography>
              </TableCell>
              <TableCell>{incident.checkName}</TableCell>
              <TableCell>
                <StatusChip status={incident.severity ?? '—'} />
              </TableCell>
              <TableCell>
                <StatusChip status={incident.status ?? '—'} />
              </TableCell>
              <TableCell>{incident.source}</TableCell>
              <TableCell>{incident.runId ?? '—'}</TableCell>
              <TableCell>{formatDateTime(incident.createdAt)}</TableCell>
              <TableCell sx={{ maxWidth: 360 }}>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {incident.summary}
                </Typography>
              </TableCell>
            </TableRow>
          ))}

          {!isLoading && incidents.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} align="center">
                <Typography variant="body2" color="text.secondary">
                  Nenhum incidente aberto no momento.
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </Paper>
  )
}

export default IncidentsTable
