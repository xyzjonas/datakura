import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { InventorySnapshotOrderSchema } from '@/client'
import InventorySnapshotOrdersPanel from '@/components/warehouse/InventorySnapshotOrdersPanel.vue'

installQuasarPlugin()

const order: InventorySnapshotOrderSchema = {
  id: 1,
  kind: 'outbound',
  code: 'WOUT-000001',
  base_order_code: 'SORD-0001',
  external_code: null,
  description: 'Prodej profilů',
  counterparty_name: 'Odběratel a.s.',
  closed_at: '2026-04-28T10:00:00Z',
  currency: 'CZK',
  total_value: '120.5000',
}

const mountIt = (
  orders: InventorySnapshotOrderSchema[],
  totals = [{ currency: 'CZK', value: '120.5' }],
) =>
  mount(InventorySnapshotOrdersPanel, {
    props: {
      title: 'Uzavřené výdeje',
      totalLabel: 'Celkové příjmy',
      totals,
      orders,
      routeName: 'warehouseOutboundOrderDetail',
      emptyLabel: 'Nic',
    },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })

describe('InventorySnapshotOrdersPanel', () => {
  it('renders order skeleton and totals', () => {
    const text = mountIt([order]).text()

    expect(text).toContain('Uzavřené výdeje')
    expect(text).toContain('Celkové příjmy')
    expect(text).toContain('WOUT-000001')
    expect(text).toContain('Odběratel a.s.')
    expect(text).toContain('Prodej profilů')
    expect(text).toContain('120,50')
  })

  it('shows the empty label and a dash instead of totals when nothing was closed', () => {
    const text = mountIt([], []).text()

    expect(text).toContain('Nic')
    expect(text).toContain('—')
    expect(text).not.toContain('Celkové příjmy')
  })

  it('falls back to dashes for missing counterparty and description', () => {
    const text = mountIt([{ ...order, counterparty_name: '', description: null }]).text()

    expect(text.match(/—/g)?.length).toBeGreaterThanOrEqual(2)
  })
})
