import { Stack, Typography } from '@mui/material'
import type { FC } from 'react'

import type { OpsDqCheck, OpsOverview, OpsPipelineJob } from '../../api/ops'
import DqChecksTable from '../ops/DqChecksTable'
import OpsOverviewCards from '../ops/OpsOverviewCards'
import PipelineStatusTable from '../ops/PipelineStatusTable'

interface OperacaoTabProps {
  overview?: OpsOverview | null
  overviewError?: Error | null
  overviewLoading: boolean
  pipelineJobs: OpsPipelineJob[]
  pipelineError?: Error | null
  pipelineLoading: boolean
  dqChecks: OpsDqCheck[]
  dqError?: Error | null
  dqLoading: boolean
}

const OperacaoTab: FC<OperacaoTabProps> = ({
  overview,
  overviewError,
  overviewLoading,
  pipelineJobs,
  pipelineError,
  pipelineLoading,
  dqChecks,
  dqError,
  dqLoading,
}) => {
  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4" gutterBottom color="text.primary">
          Operação — Saúde das Pipelines
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Monitore rapidamente o estado dos jobs, da camada de Data Quality e dos sinais com os principais indicadores do dia.
        </Typography>
      </Stack>

      <OpsOverviewCards overview={overview} isLoading={overviewLoading} error={overviewError} />

      <PipelineStatusTable jobs={pipelineJobs} isLoading={pipelineLoading} error={pipelineError} />

      <DqChecksTable checks={dqChecks} isLoading={dqLoading} error={dqError} />
    </Stack>
  )
}

export default OperacaoTab
