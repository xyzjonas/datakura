import { describe, expect, it } from 'vitest'
import {
  calculateMargin,
  calculateOrderMargin,
  formatMargin,
  formatMarginPercent,
  formatMarkupPercent,
} from '../margin'

describe('calculateMargin', () => {
  it.each([
    // selling, purchase, zisk, marže (of selling), přirážka (of purchase)
    [100, 70, 30, 30, (30 / 70) * 100],
    [120, 100, 20, (20 / 120) * 100, 20],
    [150, 100, 50, (50 / 150) * 100, 50],
    [80, 100, -20, -25, -20],
    [100, 100, 0, 0, 0],
    [50, 0, 50, 100, 0],
    [0, 50, -50, 0, -100],
    [0, 0, 0, 0, 0],
  ])('selling %d vs purchase %d', (selling, purchase, amount, percent, markupPercent) => {
    const result = calculateMargin(selling, purchase)
    expect(result.amount).toBe(amount)
    expect(result.percent).toBeCloseTo(percent, 6)
    expect(result.markupPercent).toBeCloseTo(markupPercent, 6)
  })

  it('marže is always smaller than přirážka for a gain', () => {
    const { percent, markupPercent } = calculateMargin(142.8, 100)
    expect(percent).toBeLessThan(markupPercent)
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
    expect(result?.markupPercent).toBeCloseTo(9.09, 2)
    expect(result?.percent).toBeCloseTo(8.33, 2)
  })
})

describe('formatMargin', () => {
  it('signs positive and negative', () => {
    expect(formatMargin({ amount: 5, percent: 12.34, markupPercent: 0 })).toBe('+5.00')
    expect(formatMargin({ amount: -5, percent: -12.34, markupPercent: 0 })).toBe('-5.00')
  })
})

describe('formatMarginPercent', () => {
  it.each([
    [12.34, '+12.3%'],
    [-12.34, '-12.3%'],
    [0, '+0.0%'],
  ])('formats %d as %s', (percent, expected) => {
    expect(formatMarginPercent({ amount: 0, percent, markupPercent: 0 })).toBe(expected)
  })
})

describe('formatMarkupPercent', () => {
  it.each([
    [42.84, '+42.8%'],
    [-12.34, '-12.3%'],
    [0, '+0.0%'],
  ])('formats %d as %s', (markupPercent, expected) => {
    expect(formatMarkupPercent({ amount: 0, percent: 0, markupPercent })).toBe(expected)
  })
})
