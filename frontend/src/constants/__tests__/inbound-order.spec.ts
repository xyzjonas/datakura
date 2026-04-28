import { describe, expect, it } from 'vitest'

import { getInboundOrderStep, isInboundOrderEditable } from '@/constants/inbound-order'

describe('inbound-order helpers', () => {
  it('keeps submitted order editable before warehouse order exists', () => {
    expect(
      isInboundOrderEditable({
        state: 'submitted',
        warehouse_orders: [],
      }),
    ).toBe(true)
  })

  it('marks inbound order readonly once warehouse order exists', () => {
    expect(
      isInboundOrderEditable({
        state: 'submitted',
        warehouse_orders: [
          {
            created: '2026-04-28T00:00:00Z',
            changed: '2026-04-28T00:00:00Z',
            code: 'WO2026040001',
            order_code: 'OV2026040001',
            state: 'in_transit',
          },
        ],
      }),
    ).toBe(false)
  })

  it('keeps receiving step unchanged after editability split', () => {
    expect(getInboundOrderStep({ state: 'receiving' })).toBe(3)
  })
})
