import { describe, expect, it } from 'vitest'
import {
  isBelowMinimumProfit,
  itemsBelowMinimumProfit,
  marginToMarkup,
  markupToMargin,
} from '../minimum-profit'

describe('markup <-> margin', () => {
  it.each([
    [0, 0],
    [25, 20],
    [100, 50],
    [300, 75],
  ])('markup %d %% is margin %d %%', (markup, margin) => {
    expect(markupToMargin(markup)).toBeCloseTo(margin)
    expect(marginToMarkup(margin)).toBeCloseTo(markup)
  })
})

describe('isBelowMinimumProfit', () => {
  it.each([
    // selling, purchase, min markup %, expected
    [119, 100, 20, true],
    [120, 100, 20, false], // exactly on the threshold is fine
    [119.999, 100, 20, false], // float noise
    [121, 100, 20, false],
    [90, 100, 0, false], // guard off, even on a loss
    [90, 100, null, false],
    [90, 100, undefined, false],
    [0, 100, 20, true], // free of charge
    [50, 0, 20, false], // purchase price unknown
    [0, 0, 20, false],
  ])('sell %d / buy %d / min %s %% -> %s', (selling, purchase, min, expected) => {
    expect(isBelowMinimumProfit(selling, purchase, min)).toBe(expected)
  })
})

describe('itemsBelowMinimumProfit', () => {
  const item = (unit: number, purchase: number | undefined, amount = 2) => ({
    amount,
    unit_price: unit,
    total_price: unit * amount,
    pricing_details: purchase === undefined ? null : { avg_purchase_price: purchase },
    product: { purchase_price: 50 },
  })

  it('returns only items under the threshold', () => {
    const items = [item(100, 60), item(61, 60), item(80, 60)]
    expect(itemsBelowMinimumProfit(items, 20)).toEqual([items[1]])
  })

  it('falls back to the product purchase price', () => {
    expect(itemsBelowMinimumProfit([item(55, undefined)], 20)).toHaveLength(1)
    expect(itemsBelowMinimumProfit([item(60, undefined)], 20)).toHaveLength(0)
  })

  it('handles no items / guard off', () => {
    expect(itemsBelowMinimumProfit(undefined, 20)).toEqual([])
    expect(itemsBelowMinimumProfit([item(1, 60)], 0)).toEqual([])
  })
})
