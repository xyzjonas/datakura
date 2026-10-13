import { describe, expect, it } from 'vitest'
import { calculateMargin, calculateOrderMargin, formatMargin, formatMarginPercent } from '../margin'

describe('calculateMargin', () => {
  it.each([
    [150, 100, 50, 50],
    [80, 100, -20, -20],
    [100, 100, 0, 0],
    [50, 0, 50, 0],
  ])('selling %d vs purchase %d', (selling, purchase, amount, percent) => {
    expect(calculateMargin(selling, purchase)).toEqual({ amount, percent })
  })
})

describe('calculateOrderMargin', () => {
  it('returns null without pricing details', () => {
    expect(calculateOrderMargin([{ amount: 1, unit_price: 10 }])).toBeNull()
    expect(calculateOrderMargin([])).toBeNull()
    expect(calculateOrderMargin(undefined)).toBeNull()
  })

  it('allows loss on one item when order margin stays positive', () => {
    const result = calculateOrderMargin([
      { amount: 2, unit_price: 50, total_price: 100, pricing_details: { avg_purchase_price: 40 } },
      { amount: 1, unit_price: 20, total_price: 20, pricing_details: { avg_purchase_price: 30 } },
    ])
    expect(result).toMatchObject({ sellingValue: 120, purchaseValue: 110, amount: 10 })
    expect(result?.percent).toBeCloseTo(9.09, 2)
  })
})

describe('formatMargin', () => {
  it('signs positive and negative', () => {
    expect(formatMargin({ amount: 5, percent: 12.34 })).toBe('+5.00')
    expect(formatMargin({ amount: -5, percent: -12.34 })).toBe('-5.00')
  })
})

describe('formatMarginPercent', () => {
  it.each([
    [12.34, '+12.3%'],
    [-12.34, '-12.3%'],
    [0, '+0.0%'],
  ])('formats %d as %s', (percent, expected) => {
    expect(formatMarginPercent({ amount: 0, percent })).toBe(expected)
  })
})
