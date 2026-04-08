import type { OutboundOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  icon: string
  color: string
  step: number
}

export const CANCELLED = 99

export const OUTBOUND_ORDER_STATES: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
    step: 1,
  },
  submitted: {
    label: 'Potvrzeno',
    icon: 'sym_o_approval_delegation',
    color: 'primary',
    step: 2,
  },
  picking: {
    label: 'Kompletace',
    icon: 'sym_o_handyman',
    color: 'orange-8',
    step: 3,
  },
  packing: {
    label: 'Balení',
    icon: 'sym_o_inventory_2',
    color: 'cyan-8',
    step: 4,
  },
  shipping: {
    label: 'Expedice',
    icon: 'sym_o_local_shipping',
    color: 'indigo-8',
    step: 5,
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 6,
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_block',
    color: 'negative',
    step: CANCELLED,
  },
}

export const getOutboundOrderStep = (order: Pick<OutboundOrderSchema, 'state'>) => {
  return OUTBOUND_ORDER_STATES[order.state]?.step ?? CANCELLED
}
