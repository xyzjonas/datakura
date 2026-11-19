import { describe, expect, it } from 'vitest'
import { fromBase, isForeign, toBase } from '../currency'

describe('currency helpers', () => {
  it.each([
    [2, 25, 50],
    [10.5, 24.33, 255.465],
    [0, 25, 0],
  ])('toBase(%f, %f) = %f', (amount, rate, expected) => {
    expect(toBase(amount, rate)).toBeCloseTo(expected, 6)
  })

  it.each([
    [50, 25, 2],
    [100, 0, 100], // no (valid) rate: never divides by zero
    [100, -1, 100],
  ])('fromBase(%f, %f) = %f', (amount, rate, expected) => {
    expect(fromBase(amount, rate)).toBe(expected)
  })

  it.each([
    [{ currency: 'CZK', document_currency: 'EUR' }, true],
    [{ currency: 'CZK', document_currency: 'CZK' }, false],
    [{ currency: 'CZK' }, false],
    [undefined, false],
  ])('isForeign(%j) = %s', (doc, expected) => {
    expect(isForeign(doc)).toBe(expected)
  })
})
