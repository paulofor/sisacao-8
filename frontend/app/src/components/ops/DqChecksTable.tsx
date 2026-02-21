import {
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { OpsDqCheck } from '../../api/ops'
import StatusChip from '../StatusChip'

interface DqChecksTableProps {
  checks: OpsDqCheck[]
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

const formatDate = (value: string | null) => {
  if (!value) {
    return '—'
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY') : value
}

const DqChecksTable: FC<DqChecksTableProps> = ({ checks, isLoading, error }) => {
  if (error) {
    return <Alert severity="error">Erro ao carregar os últimos data-quality checks.</Alert>
  }

  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}
    >
      <Typography variant="h6" fontWeight={600} sx={{ p: 3, pb: 0 }}>
        Últimos Data-Quality Checks
      </Typography>
      <Table size="small" aria-label="Últimos data-quality checks">
        <TableHead>
          <TableRow>
            <TableCell>Check</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Data de referência</TableCell>
            <TableCell>Criado em</TableCell>
            <TableCell>Detalhes</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading && checks.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} align="center">
                <Typography variant="body2" color="text.secondary">
                  Carregando data-quality checks...
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}

          {checks.map((check) => (
            <TableRow key={`${check.checkName}-${check.createdAt}`} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {check.checkName}
                </Typography>
              </TableCell>
              <TableCell>
                <StatusChip status={check.status ?? '—'} />
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.primary">
                  {formatDate(check.checkDate)}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.primary">
                  {formatDateTime(check.createdAt)}
                </Typography>
              </TableCell>
              <TableCell sx={{ maxWidth: 320 }}>
                {check.details ? (
                  <Tooltip title={check.details} placement="top-start">
                    <Typography variant="body2" color="text.secondary" noWrap>
                      {check.details}
                    </Typography>
                  </Tooltip>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    —
                  </Typography>
                )}
              </TableCell>
            </TableRow>
          ))}

          {!isLoading && checks.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} align="center">
                <Typography variant="body2" color="text.secondary">
                  Nenhum check de DQ disponível.
                </Typography>
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </Paper>
  )
}

export default DqChecksTable
