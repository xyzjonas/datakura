import { describe, expect, it } from 'vitest'
import { calculatePurchasePriceDelta, formatDeltaAmount, formatDeltaPercent } from '../price-impact'

describe('calculatePurchasePriceDelta', () => {
  it.each([
    // current, new, amount, percent
    [100, 110, 10, 10],
    [100, 90, -10, -10],
    [100, 100, 0, 0],
    [80, 100, 20, 25],
    [0, 50, 50, null],
  ])('%s -> %s', (current, next, amount, percent) => {
    const delta = calculatePurchasePriceDelta(current, next)
    expect(delta.amount).toBeCloseTo(amount)
    if (percent === null) {
      expect(delta.percent).toBeNull()
    } else {
      expect(delta.percent).toBeCloseTo(percent)
    }
  })
})

describe('delta formatting', () => {
  it.each([
    [100, 110, '+10.00', '+10.0 %'],
    [100, 90, '-10.00', '-10.0 %'],
    [100, 100, '0.00', '0.0 %'],
    [0, 5, '+5.00', ''],
  ])('%s -> %s', (current, next, amount, percent) => {
    const delta = calculatePurchasePriceDelta(current, next)
    expect(formatDeltaAmount(delta)).toBe(amount)
    expect(formatDeltaPercent(delta)).toBe(percent)
  })
})
