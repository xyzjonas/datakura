import type { InboundOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  icon: string
  color: string
  step: number
}

export const CANCELLED = 99

export const INBOUND_ORDER_STATES: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_draft',
    color: 'gray',
    step: 1,
  },
  submitted: {
    label: 'Potvrzeno',
    icon: 'sym_o_local_shipping',
    color: 'primary',
    step: 2,
  },
  // in_transit: {
  //   label: 'Na cestě',
  //   icon: 'sym_o_local_shipping',
  //   color: 'orange',
  // },
  // arrived: {
  //   label: 'Doručeno',
  //   icon: 'sym_o_warehouse',
  //   color: 'accent',
  // },
  // receiving: {
  //   label: 'Příjem',
  //   icon: 'sym_o_inventory',
  //   color: 'indigo',
  // },
  // quality_check: {
  //   label: 'Kontrola kvality',
  //   icon: 'sym_o_fact_check',
  //   color: 'amber',
  // },
  putaway: {
    label: 'Příjem',
    icon: 'sym_o_warehouse',
    color: 'accent',
    step: 3,
  },
  completed: {
    label: 'Dokončeno',
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
  // partially_received: {
  //   label: 'Částečně přijato',
  //   icon: 'sym_o_pending',
  //   color: 'deep-orange',
  // },
}

export const getInboundOrderStep = (order: Pick<InboundOrderSchema, 'state'>) => {
  return INBOUND_ORDER_STATES[order.state]?.step ?? CANCELLED
}
