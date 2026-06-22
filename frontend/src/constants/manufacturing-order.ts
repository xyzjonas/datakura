import type { ManufacturingOrderSchema } from '@/client'

export interface StateConfig {
  label: string
  caption?: string
  icon: string
  color: string
  step: number
}

export const CANCELLED = 99

export const MANUFACTURING_ORDER_STATES: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
    step: 1,
    caption: 'Čeká na potvrzení',
  },
  confirmed: {
    label: 'Potvrzeno',
    icon: 'sym_o_order_approve',
    color: 'primary',
    step: 2,
    caption: 'Zboží čeká na výdej na pracoviště',
  },
  in_progress: {
    label: 'Zpracovává se',
    icon: 'sym_o_manufacturing',
    color: 'orange-8',
    step: 3,
    caption: 'Zboží je na pracovišti',
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 4,
    caption: 'Výroba dokončena',
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_block',
    color: 'negative',
    step: CANCELLED,
  },
}

export const getManufacturingOrderStep = (order: Pick<ManufacturingOrderSchema, 'state'>) => {
  return MANUFACTURING_ORDER_STATES[order.state]?.step ?? CANCELLED
}

export const isManufacturingOrderEditable = (order: Pick<ManufacturingOrderSchema, 'state'>) => {
  return order.state === 'draft'
}
