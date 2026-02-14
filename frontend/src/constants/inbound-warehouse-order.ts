import type { InboundWarehouseOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  icon: string
  color: string
  step: number
}

export const CANCELLED = 99

export const INBOUND_WAREHOUSE_ORDER_STATES: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
    step: 1,
  },
  pending: {
    label: 'Připraveno',
    icon: 'sym_o_pallet',
    color: 'orange-8',
    step: 2,
  },
  started: {
    label: 'Příjem zahájen',
    icon: 'sym_o_avg_pace',
    color: 'cyan-8',
    step: 3,
  },
  completed: {
    label: 'Přijato',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 4,
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_cancel',
    color: 'negative',
    step: CANCELLED,
  },
}

export const getInboundWarehouseOrderStep = (
  order?: Pick<InboundWarehouseOrderSchema, 'state'>,
) => {
  if (!order) {
    return CANCELLED
  }
  return INBOUND_WAREHOUSE_ORDER_STATES[order.state]?.step ?? CANCELLED
}
