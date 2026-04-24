export type InvoiceDetailOrderItemLike = {
  index: number
  amount: number
  unit_price: number
  total_price: number
  product: {
    code: string
    name: string
    unit?: string | null
  }
}

export type InvoiceDetailOrderLike = {
  code: string
  external_code?: string | null
  state: string
  items?: InvoiceDetailOrderItemLike[]
}

export type InvoiceDetailLike = {
  outbound_orders?: InvoiceDetailOrderLike[]
  inbound_orders?: InvoiceDetailOrderLike[]
}

export type InvoiceDetailDirection = 'outbound' | 'inbound'

export const getInvoiceDetailDirection = (invoice?: InvoiceDetailLike): InvoiceDetailDirection => {
  if ((invoice?.outbound_orders ?? []).length > 0) {
    return 'outbound'
  }

  return 'inbound'
}

export const getInvoiceDetailOrders = (invoice?: InvoiceDetailLike): InvoiceDetailOrderLike[] => {
  if (!invoice) {
    return []
  }

  return getInvoiceDetailDirection(invoice) === 'outbound'
    ? (invoice.outbound_orders ?? [])
    : (invoice.inbound_orders ?? [])
}

export const getInvoiceDetailOrderTotal = (order: InvoiceDetailOrderLike) =>
  (order.items ?? []).reduce((sum, item) => sum + item.total_price, 0)

export const getInvoiceDetailTotal = (invoice?: InvoiceDetailLike) =>
  getInvoiceDetailOrders(invoice).reduce((sum, order) => sum + getInvoiceDetailOrderTotal(order), 0)
