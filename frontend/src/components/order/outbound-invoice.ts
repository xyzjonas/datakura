import type { OutboundInvoiceCreateSchema, OutboundOrderSchema } from '@/client'

type InvoiceSelectionReason =
  | 'already-invoiced'
  | 'draft'
  | 'cancelled'
  | 'warehouse-not-completed'
  | 'different-customer'
  | 'different-currency'

const toIsoDate = (date: Date) => date.toISOString().split('T')[0]

const addDays = (date: Date, days: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

const hasCompletedWarehouseOrder = (order: OutboundOrderSchema) => {
  const warehouseOrders = order.warehouse_orders ?? []
  return (
    warehouseOrders.length > 0 &&
    warehouseOrders.every((warehouseOrder) => warehouseOrder.state === 'completed')
  )
}

export const getOutboundInvoiceSelectionBlockReason = (
  order: OutboundOrderSchema,
  anchorOrder?: OutboundOrderSchema,
): InvoiceSelectionReason | null => {
  if (order.invoice) {
    return 'already-invoiced'
  }

  if (order.state === 'draft') {
    return 'draft'
  }

  if (order.state === 'cancelled') {
    return 'cancelled'
  }

  if (!hasCompletedWarehouseOrder(order)) {
    return 'warehouse-not-completed'
  }

  if (!anchorOrder) {
    return null
  }

  if (anchorOrder.customer.code !== order.customer.code) {
    return 'different-customer'
  }

  if (anchorOrder.currency !== order.currency) {
    return 'different-currency'
  }

  return null
}

export const canGroupOutboundOrderForInvoice = (
  order: OutboundOrderSchema,
  anchorOrder?: OutboundOrderSchema,
) => getOutboundInvoiceSelectionBlockReason(order, anchorOrder) === null

export const createDefaultOutboundInvoiceForm = (
  selectedOrders: OutboundOrderSchema[],
): OutboundInvoiceCreateSchema => {
  const today = new Date()
  const dueDays = selectedOrders[0]?.customer.invoice_due_days ?? 14

  return {
    order_codes: selectedOrders.map((order) => order.code),
    issued_date: toIsoDate(today),
    due_date: toIsoDate(addDays(today, dueDays)),
    payment_method_name: selectedOrders[0]?.customer.default_payment_method?.name ?? undefined,
    external_code: undefined,
    taxable_supply_date: toIsoDate(today),
    paid_date: undefined,
    note: undefined,
  }
}

export const outboundInvoiceSelectionReasonLabel: Record<InvoiceSelectionReason, string> = {
  'already-invoiced': 'Objednavka uz ma pripojenou fakturu.',
  draft: 'Nejdriv potvrdte objednavku.',
  cancelled: 'Zrusenou objednavku nelze fakturovat.',
  'warehouse-not-completed': 'Fakturu lze vytvorit az po dokonceni vydejky.',
  'different-customer': 'Do jedne faktury lze vybrat jen objednavky stejneho odberatele.',
  'different-currency': 'Do jedne faktury lze vybrat jen objednavky ve stejne mene.',
}
