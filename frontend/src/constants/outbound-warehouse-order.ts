import type { OutboundWarehouseOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  icon: string
  color: string
}

export const OUTBOUND_WAREHOUSE_ORDER_STATES: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
  },
  pending: {
    label: 'Připraveno',
    icon: 'sym_o_pallet',
    color: 'orange-8',
  },
  started: {
    label: 'Zahájeno',
    icon: 'sym_o_avg_pace',
    color: 'cyan-8',
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_cancel',
    color: 'negative',
  },
}

export const getOutboundWarehouseOrderStateLabel = (
  order: Pick<OutboundWarehouseOrderSchema, 'state'>,
) => {
  return OUTBOUND_WAREHOUSE_ORDER_STATES[order.state]?.label ?? order.state
}
