import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import type { InventorySnapshotOrderSchema } from '@/client'
import InventorySnapshotOrdersDialog from '@/components/warehouse/InventorySnapshotOrdersDialog.vue'

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

let wrapper: ReturnType<typeof mount> | undefined

const mountIt = async (orders: InventorySnapshotOrderSchema[]) => {
  wrapper = mount(InventorySnapshotOrdersDialog, {
    props: {
      show: true,
      title: 'Uzavřené výdejky',
      subtitle: 'podtitul',
      orders,
      routeName: 'warehouseOutboundOrderDetail',
      emptyLabel: 'Nic',
    },
    attachTo: document.body,
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
  await flushPromises()
}

afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('InventorySnapshotOrdersDialog', () => {
  it('renders the order skeleton', async () => {
    await mountIt([order])
    const text = document.body.textContent ?? ''

    expect(text).toContain('Uzavřené výdejky')
    expect(text).toContain('WOUT-000001')
    expect(text).toContain('Odběratel a.s.')
    expect(text).toContain('Prodej profilů')
    expect(text).toContain('120,50')
  })

  it('falls back to dashes for missing counterparty and description', async () => {
    await mountIt([{ ...order, counterparty_name: '', description: null }])

    expect((document.body.textContent ?? '').match(/—/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('shows the empty label without orders', async () => {
    await mountIt([])

    expect(document.body.textContent).toContain('Nic')
  })
})
