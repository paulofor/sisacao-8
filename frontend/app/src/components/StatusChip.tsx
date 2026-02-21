import { Chip, type ChipProps } from '@mui/material'
import type { FC } from 'react'

const mapStatusToColor = (status: string): ChipProps['color'] => {
  const normalized = status.toUpperCase()

  if (
    normalized.includes('FAIL') ||
    normalized.includes('ERROR') ||
    normalized.includes('CRITICAL') ||
    normalized.includes('DOWN') ||
    normalized.includes('BLOCK')
  ) {
    return 'error'
  }

  if (
    normalized.includes('WARN') ||
    normalized.includes('SILENT') ||
    normalized.includes('DELAY') ||
    normalized.includes('PENDING') ||
    normalized.includes('MEDIUM')
  ) {
    return 'warning'
  }

  if (
    normalized.includes('OK') ||
    normalized.includes('PASS') ||
    normalized.includes('SUCCESS') ||
    normalized.includes('READY') ||
    normalized.includes('ON') ||
    normalized.includes('LOW')
  ) {
    return 'success'
  }

  return 'default'
}

interface StatusChipProps {
  status?: string | null
  size?: ChipProps['size']
  variant?: ChipProps['variant']
}

const StatusChip: FC<StatusChipProps> = ({ status, size = 'small', variant = 'filled' }) => {
  const label = status?.toString().trim() || '—'
  const color = status ? mapStatusToColor(status) : 'default'

  return <Chip label={label} color={color} size={size} variant={variant} sx={{ fontWeight: 600 }} />
}

export default StatusChip
