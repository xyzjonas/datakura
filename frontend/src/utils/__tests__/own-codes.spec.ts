import { describe, expect, it } from 'vitest'
import { itemsMissingOwnCode } from '../own-codes'

const order = (requires: boolean | undefined, codes: (string | null | undefined)[]) => ({
  customer: { requires_own_codes: requires },
  items: codes.map((customer_product_code) => ({ customer_product_code })),
})

describe('itemsMissingOwnCode', () => {
  it('returns nothing for customers not ordering by own codes', () => {
    expect(itemsMissingOwnCode(order(false, [null, 'A']))).toEqual([])
    expect(itemsMissingOwnCode(order(undefined, [null]))).toEqual([])
  })

  it.each([
    [['A', 'B'], 0],
    [['A', null], 1],
    [[null, undefined, ''], 3],
    [[], 0],
  ])('counts items lacking a code %j -> %i', (codes, missing) => {
    expect(itemsMissingOwnCode(order(true, codes))).toHaveLength(missing)
  })

  it('copes with an order without items', () => {
    expect(itemsMissingOwnCode({ customer: { requires_own_codes: true } })).toEqual([])
  })
})
