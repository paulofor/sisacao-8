import {
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'
import dayjs from 'dayjs'
import type { FC } from 'react'

import type { DataCollectionMessage, DataCollectionMessageSeverity } from '../api/dataCollections'

const severityColorMap: Partial<Record<DataCollectionMessageSeverity, 'default' | 'success' | 'warning' | 'error'>> = {
  SUCCESS: 'success',
  INFO: 'default',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'error',
}

const formatDate = (value: string) => {
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('DD/MM/YYYY HH:mm:ss') : value
}

interface DataCollectionMessagesTableProps {
  messages: DataCollectionMessage[]
}

const DataCollectionMessagesTable: FC<DataCollectionMessagesTableProps> = ({ messages }) => {
  return (
    <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <Table size="small" aria-label="Mensagens de coletas de dados">
        <TableHead>
          <TableRow>
            <TableCell width="18%">Data / Hora</TableCell>
            <TableCell width="16%">Coletor</TableCell>
            <TableCell width="20%">Dataset / Tabela</TableCell>
            <TableCell>Mensagem</TableCell>
            <TableCell align="right" width="12%">
              Severidade
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {messages.map((message) => {
            const chipColor = severityColorMap[message.severity as DataCollectionMessageSeverity] ?? 'default'
            const hasMetadata = message.metadata && Object.keys(message.metadata).length > 0
            return (
              <TableRow key={message.id} hover>
                <TableCell>
                  <Typography variant="body2" color="text.primary">
                    {formatDate(message.createdAt)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={600} color="text.primary">
                    {message.collector}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {message.dataset}
                  </Typography>
                </TableCell>
                <TableCell sx={{ maxWidth: 420 }}>
                  <Tooltip title={message.summary} placement="top-start">
                    <Typography variant="body2" color="text.primary" noWrap>
                      {message.summary}
                    </Typography>
                  </Tooltip>
                  {hasMetadata ? (
                    <Box mt={0.75}>
                      <Typography variant="caption" color="text.secondary">
                        {JSON.stringify(message.metadata)}
                      </Typography>
                    </Box>
                  ) : null}
                </TableCell>
                <TableCell align="right">
                  <Chip
                    size="small"
                    label={message.severity}
                    color={chipColor}
                    sx={{ fontWeight: 600 }}
                  />
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {messages.length === 0 ? (
        <Box p={3} textAlign="center">
          <Typography variant="body2" color="text.secondary">
            Nenhuma mensagem encontrada para os filtros selecionados.
          </Typography>
        </Box>
      ) : null}
    </TableContainer>
  )
}

export default DataCollectionMessagesTable

