// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
export type StatusConfig = {
    color: string
    icon: string
    label: string
    spin?: boolean
}

export const STATUS_CONFIG: Record<string, StatusConfig> = {
    PENDING:   { color: 'rgb(234, 179, 8)',   icon: 'solar:clock-circle-linear',  label: 'Pending' },
    RUNNING:   { color: 'rgb(59, 130, 246)',  icon: 'solar:refresh-bold',          label: 'Running',  spin: true },
    COMPLETED: { color: '#4CAF50',            icon: 'solar:check-circle-linear',  label: 'Completed' },
    FAILED:    { color: 'rgb(239, 68, 68)',   icon: 'solar:close-circle-linear',  label: 'Failed' },
    PAUSED:    { color: 'rgb(249, 115, 22)',  icon: 'solar:pause-circle-linear',  label: 'Paused' },
    CANCELED:  { color: 'rgb(156, 163, 175)', icon: 'solar:close-circle-linear',  label: 'Canceled' },
    CANCELLED: { color: 'rgb(156, 163, 175)', icon: 'solar:close-circle-linear',  label: 'Cancelled' },
}

const DEFAULT_CONFIG: StatusConfig = {
    color: 'rgb(156, 163, 175)',
    icon: 'solar:minus-circle-linear',
    label: 'No status',
}

export function getStatusConfig(status: string | null | undefined): StatusConfig {
    return STATUS_CONFIG[status?.toUpperCase() ?? ''] ?? DEFAULT_CONFIG
}

export function getStatusColor(status: string | null | undefined): string {
    return getStatusConfig(status).color
}

// Opacity for segmented node progress bars (unexecuted nodes = nearly invisible)
export function getStatusOpacity(status: string | null | undefined): number {
    switch (status?.toUpperCase()) {
        case 'COMPLETED': return 1
        case 'RUNNING':   return 0.9
        case 'FAILED':    return 1
        case 'PAUSED':    return 0.7
        case 'PENDING':   return 0.35
        default:          return 0.12
    }
}
