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
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
    step: 1,
  },
  submitted: {
    label: 'Potvrzeno',
    icon: 'sym_o_delivery_truck_speed',
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
  receiving: {
    label: 'Příjem',
    icon: 'sym_o_fact_check',
    color: 'orange-8',
    step: 3,
  },
  putaway: {
    label: 'Naskladnění',
    icon: 'sym_o_input',
    color: 'cyan-8',
    step: 4,
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 5,
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
