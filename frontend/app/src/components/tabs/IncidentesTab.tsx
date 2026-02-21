import { Stack, Typography } from '@mui/material'
import type { FC } from 'react'

import type { OpsIncident } from '../../api/ops'
import IncidentsTable from '../ops/IncidentsTable'

interface IncidentesTabProps {
  incidents: OpsIncident[]
  incidentsError?: Error | null
  incidentsLoading: boolean
}

const IncidentesTab: FC<IncidentesTabProps> = ({ incidents, incidentsError, incidentsLoading }) => {
  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Incidentes Operacionais
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Acompanhe os incidentes em aberto (status OPEN/INVESTIGATING) com suas respectivas severidades, links e IDs para
          agilizar a triagem com o time de operações.
        </Typography>
      </Stack>

      <IncidentsTable incidents={incidents} isLoading={incidentsLoading} error={incidentsError} />
    </Stack>
  )
}

export default IncidentesTab
