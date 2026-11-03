import { describe, expect, it } from 'vitest'
import type { WarehouseItemSchema } from '@/client'
import { aggregatePackaging } from '../aggregatePackaging'

const item = (overrides: Record<string, unknown> = {}) =>
  ({
    id: 1,
    amount: 10,
    unit_of_measure: 'KS',
    product: { code: 'P1' },
    package: { type: 'BAG-10' },
    batch: null,
    ...overrides,
  }) as unknown as WarehouseItemSchema

describe('aggregatePackaging', () => {
  it('sums identical packages and counts them', () => {
    const rows = aggregatePackaging([item({ id: 1 }), item({ id: 2 })])

    expect(rows).toHaveLength(1)
    expect(rows[0]!.amount).toBe(20)
    expect(rows[0]!.itemsCount).toBe(2)
  })

  it('never merges different batches (e.g. differently certified goods)', () => {
    const rows = aggregatePackaging([
      item({ id: 1, batch: { id: 1 } }),
      item({ id: 2, batch: { id: 2 } }),
      item({ id: 3, batch: { id: 2 } }),
      item({ id: 4, batch: null }),
    ])

    expect(rows).toHaveLength(3)
    const countByBatch = Object.fromEntries(
      rows.map((r) => [String(r.batch?.id ?? 'none'), r.itemsCount]),
    )
    expect(countByBatch).toEqual({ '1': 1, '2': 2, none: 1 })
  })

  it('still separates package types and products', () => {
    const rows = aggregatePackaging([
      item({ id: 1 }),
      item({ id: 2, package: { type: 'BAG-20' } }),
      item({ id: 3, product: { code: 'P2' } }),
    ])

    expect(rows).toHaveLength(3)
  })
})
