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
    step: 3,
  },
  shipping: {
    label: 'Expedice',
    icon: 'sym_o_local_shipping',
    color: 'indigo-8',
    step: 3,
  },
  sent: {
    label: 'Odesláno',
    icon: 'sym_o_send',
    color: 'blue-8',
    step: 4,
  },
  invoiced: {
    label: 'Vyfakturováno',
    icon: 'sym_o_receipt_long',
    color: 'teal-7',
    step: 5,
  },
  waiting_for_payment: {
    label: 'Čeká na úhradu',
    icon: 'sym_o_hourglass_top',
    color: 'amber-8',
    step: 6,
  },
  completed_paid: {
    label: 'Uhrazeno',
    icon: 'sym_o_paid',
    color: 'positive',
    step: 7,
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
    step: 7,
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
