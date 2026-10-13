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
