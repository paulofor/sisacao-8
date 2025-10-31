import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import InfoIcon from '@mui/icons-material/Info'
import {
  Alert,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material'

import type { GoogleFinanceParserTestResult } from '../api/testResults'

const statusIcon = (status: GoogleFinanceParserTestResult['status']) => {
  if (status === 'passed') {
    return <CheckCircleIcon color="success" />
  }
  if (status === 'failed') {
    return <ErrorIcon color="error" />
  }
  return <InfoIcon color="info" />
}

interface GoogleFinanceParserTestCardProps {
  result?: GoogleFinanceParserTestResult
  isLoading: boolean
  error?: Error | null
}

const GoogleFinanceParserTestCard = ({ result, isLoading, error }: GoogleFinanceParserTestCardProps) => {
  if (isLoading && !result) {
    return (
      <Card>
        <CardHeader title="Saúde do Parser do Google Finance" />
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="center">
            <CircularProgress size={24} />
            <Typography variant="body2" color="text.secondary">
              Carregando resultado do teste…
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Saúde do Parser do Google Finance" />
        <CardContent>
          <Alert severity="error">Não foi possível obter o resultado do teste. {error.message}</Alert>
        </CardContent>
      </Card>
    )
  }

  if (!result) {
    return null
  }

  const { status, description, details, updatedAt } = result
  const updatedAtDate = new Date(updatedAt)
  const updatedAtLabel = Number.isNaN(updatedAtDate.getTime())
    ? 'Data indisponível'
    : updatedAtDate.toLocaleString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        dateStyle: 'short',
        timeStyle: 'short',
      })

  return (
    <Card>
      <CardHeader
        avatar={statusIcon(status)}
        title="Saúde do Parser do Google Finance"
        subheader={description}
      />
      <CardContent>
        <Stack spacing={1}>
          <Typography variant="body2" color="text.secondary">
            Ticker monitorado: <strong>{details.ticker}</strong> ({details.exchange})
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Valor encontrado no HTML: <strong>{details.priceText}</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Valor interpretado pelo parser: <strong>{details.parsedPrice.toFixed(2)}</strong>
          </Typography>
          {details.previousError ? (
            <Alert severity="info">
              Última falha registrada: {details.previousError}
            </Alert>
          ) : null}
          <Typography variant="caption" color="text.disabled">
            Fonte: {details.htmlFixture} • Atualizado em {updatedAtLabel}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}

export default GoogleFinanceParserTestCard

