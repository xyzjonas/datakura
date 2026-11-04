import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { InventorySnapshotDetailSchema } from '@/client'
import InventorySnapshotHeader from '@/components/warehouse/InventorySnapshotHeader.vue'
import { getSnapshotGrossGain } from '@/views/inventory-snapshot'

installQuasarPlugin()

const snapshot = {
  id: 1,
  line_count: 15229,
  purchase_totals: [{ currency: 'CZK', value: '1000.0000' }],
  receipt_totals: [{ currency: 'CZK', value: '700.0000' }],
  expenditure_totals: [{ currency: 'CZK', value: '300.0000' }],
  gain_totals: [{ currency: 'CZK', value: '500.0000' }],
  inbound_orders: [],
  outbound_orders: [],
} as unknown as InventorySnapshotDetailSchema

const mountIt = (overrides: Partial<InventorySnapshotDetailSchema> = {}, mode = 'purchase') =>
  mount(InventorySnapshotHeader, {
    props: { snapshot: { ...snapshot, ...overrides }, valuationMode: mode as 'purchase' },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })

describe('getSnapshotGrossGain', () => {
  it.each([
    [[{ currency: 'CZK', value: '500' }], [{ currency: 'CZK', value: '300' }], '200.0000'],
    [[{ currency: 'CZK', value: '100' }], [{ currency: 'CZK', value: '300' }], '-200.0000'],
    [[], [{ currency: 'CZK', value: '300' }], '-300.0000'],
    [[{ currency: 'CZK', value: '300' }], [], '300.0000'],
  ])('computes %j - %j', (gains, spend, expected) => {
    expect(getSnapshotGrossGain({ gain_totals: gains, expenditure_totals: spend })[0]?.value).toBe(
      expected,
    )
  })

  it('keeps currencies apart and handles nothing closed', () => {
    expect(
      getSnapshotGrossGain({
        gain_totals: [{ currency: 'EUR', value: '5' }],
        expenditure_totals: [{ currency: 'CZK', value: '2' }],
      }),
    ).toEqual([
      { currency: 'CZK', value: '-2.0000' },
      { currency: 'EUR', value: '5.0000' },
    ])
    expect(getSnapshotGrossGain({ gain_totals: [], expenditure_totals: [] })).toEqual([])
  })
})

describe('InventorySnapshotHeader', () => {
  it('shows all summary cells', () => {
    const text = mountIt().text()

    expect(text).toContain('15229')
    expect(text).toContain('Hodnota skladu (při uložení)')
    expect(text).toContain('Výdaje')
    expect(text).toContain('Příjmy')
    expect(text).toContain('Hrubý zisk')
    expect(text).toContain('+200,00')
  })

  it('switches stock value with the valuation mode', () => {
    const wrapper = mountIt({}, 'receipt')

    expect(wrapper.text()).toContain('Hodnota skladu (při příjmu)')
    expect(wrapper.text()).toContain('700,00')
    expect(wrapper.text()).not.toContain('1 000,00')
  })

  it('colours a loss red and a gain green', () => {
    expect(mountIt().find('.text-positive').exists()).toBe(true)
    const loss = mountIt({ gain_totals: [] })
    expect(loss.find('.text-negative').exists()).toBe(true)
    expect(loss.text()).toContain('-300,00')
  })

  it('shows dashes when no orders were closed', () => {
    const text = mountIt({ expenditure_totals: [], gain_totals: [] }).text()

    expect(text.match(/—/g)?.length).toBe(3)
  })
})
