import {
  getInvoiceDetailDirection,
  getInvoiceDetailOrderTotal,
  getInvoiceDetailOrders,
  getInvoiceDetailTotal,
  type InvoiceDetailLike,
} from '../invoice-detail'
import { describe, expect, it } from 'vitest'

const createItem = (total_price: number) => ({
  index: 0,
  amount: 1,
  unit_price: total_price,
  total_price,
  product: {
    code: 'SKU-1',
    name: 'Product',
  },
})

describe('invoice detail helpers', () => {
  it('uses outbound groups when outbound invoice', () => {
    const invoice: InvoiceDetailLike = {
      outbound_orders: [
        {
          code: 'SORD-1',
          state: 'completed',
          items: [createItem(120), createItem(30)],
        },
      ],
      inbound_orders: [
        {
          code: 'ORD-1',
          state: 'completed',
          items: [createItem(999)],
        },
      ],
    }

    expect(getInvoiceDetailDirection(invoice)).toBe('outbound')
    expect(getInvoiceDetailOrders(invoice).map((order) => order.code)).toEqual(['SORD-1'])
    expect(getInvoiceDetailOrderTotal(getInvoiceDetailOrders(invoice)[0]!)).toBe(150)
    expect(getInvoiceDetailTotal(invoice)).toBe(150)
  })

  it('uses inbound groups when no outbound groups present', () => {
    const invoice: InvoiceDetailLike = {
      outbound_orders: [],
      inbound_orders: [
        {
          code: 'ORD-1',
          state: 'completed',
          items: [createItem(75.5), createItem(24.5)],
        },
      ],
    }

    expect(getInvoiceDetailDirection(invoice)).toBe('inbound')
    expect(getInvoiceDetailOrders(invoice).map((order) => order.code)).toEqual(['ORD-1'])
    expect(getInvoiceDetailTotal(invoice)).toBe(100)
  })
})
