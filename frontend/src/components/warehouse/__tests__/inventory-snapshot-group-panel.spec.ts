import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { InventorySnapshotLineSchema } from '@/client'
import { groupSnapshotLinesByProduct } from '@/views/inventory-snapshot'
import InventorySnapshotGroupPanel from '../InventorySnapshotGroupPanel.vue'

installQuasarPlugin()

vi.mock('@/composables/use-app-router', () => ({
  useAppRouter: () => ({ goToProduct: vi.fn() }),
}))

const lines: InventorySnapshotLineSchema[] = Array.from({ length: 50 }, (_, i) => ({
  id: i + 1,
  warehouse_item_id: i + 100,
  warehouse_item_id_at_snapshot: i + 100,
  product_code: 'SKU-1',
  product_name: 'Produkt',
  location_code: `L-${i}`,
  quantity: '1.0000',
  unit_of_measure: 'ks',
  tracking_level: 'FUNGIBLE',
  purchase_currency: 'CZK',
  purchase_unit_price: '1.0000',
  purchase_line_value: '1.0000',
  receipt_currency: 'CZK',
  receipt_unit_price: '1.0000',
  receipt_line_value: '1.0000',
  receipt_price_available: true,
  receipt_price_fallback_reason: null,
}))

const mountIt = () => {
  const [group] = groupSnapshotLinesByProduct(lines)
  return mount(InventorySnapshotGroupPanel, {
    props: { group: group!, valuationMode: 'purchase' },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
}

describe('InventorySnapshotGroupPanel', () => {
  it('shows the group summary but does not render the line rows while collapsed', () => {
    const wrapper = mountIt()
    expect(wrapper.text()).toContain('Produkt')
    expect(wrapper.text()).toContain('SKU-1')
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })

  it('renders all lines once opened and keeps them when collapsed again', async () => {
    const wrapper = mountIt()
    await wrapper.find('.q-item').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(50)

    await wrapper.find('.q-item').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(50)
  })
})
