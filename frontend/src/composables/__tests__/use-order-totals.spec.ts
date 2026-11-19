import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { useOrderTotals, type OrderTotalsSource } from '../use-order-totals'

describe('useOrderTotals', () => {
  it.each([null, undefined, { currency: 'CZK' }, { currency: 'CZK', items: [] }])(
    'handles empty order %j',
    (order) => {
      const totals = useOrderTotals(order)
      expect(totals.totalPrice.value).toBe(0)
      expect(totals.orderMargin.value).toBeNull()
      expect(totals.formattedPurchaseValue.value).toBe('0')
    },
  )

  it('prefers total_price over amount * unit_price', () => {
    const { totalPrice } = useOrderTotals({
      currency: 'CZK',
      items: [
        { amount: 2, unit_price: 10, total_price: 15 },
        { amount: 3, unit_price: 5 },
      ],
    })
    expect(totalPrice.value).toBe(30)
  })

  it('reacts to ref changes and computes margin', () => {
    const order = ref<OrderTotalsSource>({ currency: 'CZK', items: [] })
    const { totalPrice, currency, orderMargin, formattedPurchaseValue } = useOrderTotals(order)
    order.value = {
      currency: 'EUR',
      items: [{ amount: 2, unit_price: 50, pricing_details: { avg_purchase_price: 40 } }],
    }
    expect(totalPrice.value).toBe(100)
    expect(currency.value).toBe('EUR')
    expect(orderMargin.value).toMatchObject({ purchaseValue: 80, amount: 20 })
    expect(formattedPurchaseValue.value).toContain('80')
  })
})

describe('useOrderTotals with returned goods', () => {
  const priced = (amount: number, unit: number, purchase: number, is_returned = false) => ({
    amount,
    unit_price: unit,
    total_price: amount * unit,
    is_returned,
    pricing_details: { avg_purchase_price: purchase },
    product: { unit_weight: 2 },
  })

  it('subtracts returned rows from price, margin and weight', () => {
    // sold 10 x 100 (bought for 60), 4 of them came back
    const totals = useOrderTotals({
      currency: 'CZK',
      items: [priced(10, 100, 60), priced(4, 100, 60, true)],
    })

    expect(totals.totalPrice.value).toBe(600)
    expect(totals.orderMargin.value).toMatchObject({
      sellingValue: 600,
      purchaseValue: 360,
      amount: 240,
    })
    expect(totals.totalWeight.value).toBe(12)
  })

  it('a fully returned order has nothing left', () => {
    const totals = useOrderTotals({
      currency: 'CZK',
      items: [priced(3, 50, 20), priced(3, 50, 20, true)],
    })

    expect(totals.totalPrice.value).toBe(0)
    expect(totals.orderMargin.value).toMatchObject({ sellingValue: 0, purchaseValue: 0, amount: 0 })
    expect(totals.totalWeight.value).toBe(0)
  })
})

describe('useOrderTotals foreign currency', () => {
  const order: OrderTotalsSource = {
    currency: 'CZK',
    document_currency: 'EUR',
    items: [
      { amount: 2, unit_price: 50, total_price: 100, document_total_price: 4 },
      // goods taken back are subtracted from both
      { amount: 1, unit_price: 50, total_price: 50, document_total_price: 2, is_returned: true },
    ],
  }

  it('sums the document prices in the document currency, the base ones separately', () => {
    const totals = useOrderTotals(order)
    expect(totals.isForeign.value).toBe(true)
    expect(totals.documentCurrency.value).toBe('EUR')
    expect(totals.documentTotalPrice.value).toBe(2)
    expect(totals.currency.value).toBe('CZK')
    expect(totals.totalPrice.value).toBe(50)
  })

  it('is not foreign without a document currency (inbound) or when it is the base one', () => {
    expect(useOrderTotals({ currency: 'CZK', items: [] }).isForeign.value).toBe(false)
    expect(
      useOrderTotals({ currency: 'CZK', document_currency: 'CZK', items: [] }).isForeign.value,
    ).toBe(false)
  })

  it('falls back to the base total when an item has no document price', () => {
    const { documentTotalPrice } = useOrderTotals({
      currency: 'CZK',
      items: [{ amount: 2, unit_price: 10, total_price: 15 }],
    })
    expect(documentTotalPrice.value).toBe(15)
  })
})
