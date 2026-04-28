import type { InboundOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  caption?: string
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
    caption: 'Čeká na potvrzení',
  },
  submitted: {
    label: 'Objednáno',
    icon: 'sym_o_delivery_truck_speed',
    color: 'primary',
    step: 2,
    caption: 'Zboží je na cestě',
  },
  receiving: {
    label: 'Příjem',
    icon: 'sym_o_fact_check',
    color: 'orange-8',
    step: 3,
    caption: 'Zboží čeká na příjem',
  },
  putaway: {
    label: 'Naskladnění',
    icon: 'sym_o_input',
    color: 'cyan-8',
    step: 4,
    caption: 'Zboží je připraveno k naskladnění',
  },
  completed: {
    label: 'Přijato',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 5,
    caption: 'Zboží bylo naskladněno',
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_block',
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

export const isInboundOrderEditable = (
  order: Pick<InboundOrderSchema, 'state' | 'warehouse_orders'>,
) => {
  const warehouseOrderCount = order.warehouse_orders?.length ?? 0
  return ['draft', 'submitted'].includes(order.state) && warehouseOrderCount === 0
}
