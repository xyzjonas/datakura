import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { InboundOrderSchema } from '@/client'
import TotalWeight from '../TotalWeight.vue'

installQuasarPlugin()

function makeItem(amount: number, unit_weight: number) {
  return {
    created: '2024-01-01',
    changed: '2024-01-01',
    amount,
    unit_price: 0,
    total_price: 0,
    index: 0,
    product: {
      created: '2024-01-01',
      changed: '2024-01-01',
      name: 'Test Product',
      code: 'TEST',
      type: 'physical',
      unit: 'pcs',
      unit_weight,
      base_price: 0,
      purchase_price: 0,
      no_discount: false,
      disallow_unpacking: false,
      currency: 'EUR',
    },
  }
}

const BASE_ORDER: InboundOrderSchema = {
  created: '2024-01-01',
  changed: '2024-01-01',
  code: 'TEST-001',
  type: 'inbound' as unknown as InboundOrderSchema['type'],
  customer: {} as InboundOrderSchema['customer'],
  supplier: {} as InboundOrderSchema['supplier'],
  state: 'open',
  currency: 'EUR',
}

function mountOrder(items?: ReturnType<typeof makeItem>[]) {
  return mount(TotalWeight, {
    props: { order: { ...BASE_ORDER, items } as InboundOrderSchema },
  })
}

function chipText(wrapper: ReturnType<typeof mount>): string {
  return wrapper.find('.q-chip').text()
}

describe('TotalWeight', () => {
  it('shows 0.00 g when items is undefined', () => {
    const wrapper = mountOrder(undefined)
    expect(chipText(wrapper)).toContain('0.00')
  })

  it('shows 0.00 g for an empty items array', () => {
    const wrapper = mountOrder([])
    expect(chipText(wrapper)).toContain('0.00')
  })

  it('computes weight for a single item', () => {
    const wrapper = mountOrder([makeItem(3, 100)])
    // 3 * 100 = 300.00 g
    expect(chipText(wrapper)).toContain('300.00')
  })

  it('sums weight across multiple items', () => {
    const wrapper = mountOrder([makeItem(2, 50), makeItem(4, 25)])
    // 2*50 + 4*25 = 100 + 100 = 200.00 g
    expect(chipText(wrapper)).toContain('200.00')
  })

  it('handles float unit weights without floating-point drift', () => {
    const wrapper = mountOrder([makeItem(1, 0.1), makeItem(1, 0.2)])
    // 0.1 + 0.2 = 0.3 — JS gives 0.30000000000000004 which toFixed(2) rounds to "0.30"
    expect(chipText(wrapper)).toContain('0.30')
  })

  it('handles float amount and unit_weight combination', () => {
    // 3 items each 0.575 g → expect 1.73 g total (3 * 0.575 = 1.725 → rounds to 1.73)
    const wrapper = mountOrder([makeItem(1, 0.575), makeItem(1, 0.575), makeItem(1, 0.575)])
    expect(chipText(wrapper)).toContain('1.73')
  })

  it('treats null unit_weight as 0 without NaN or crash', () => {
    // API may return null despite the type saying number; guarded with ?? 0.
    const item = makeItem(5, null as unknown as number)
    const wrapper = mountOrder([item])
    expect(chipText(wrapper)).toContain('0.00')
    expect(chipText(wrapper)).not.toContain('NaN')
  })

  it('treats undefined unit_weight as 0 without NaN or crash', () => {
    const item = makeItem(5, undefined as unknown as number)
    const wrapper = mountOrder([item])
    expect(chipText(wrapper)).toContain('0.00')
    expect(chipText(wrapper)).not.toContain('NaN')
  })
})
