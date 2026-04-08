import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import SimpleInboundOrdersTable from '../SimpleInboundOrdersTable.vue'

vi.mock('@/client', () => ({
  warehouseApiRoutesInboundOrdersGetInboundOrders: vi.fn().mockResolvedValue({
    data: {
      data: [
        {
          code: 'IN-123',
          state: 'new',
          created: '2026-01-01T12:00:00Z',
          supplier: { name: 'Supplier X' },
          items: [{ amount: 2, unit_price: 10 }],
          currency: 'CZK',
        },
      ],
      count: 1,
    },
  }),
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (result: { data?: unknown }) => result.data,
  }),
}))

installQuasarPlugin()

describe('SimpleInboundOrdersTable', () => {
  it('fetches inbound orders and renders the table row content', async () => {
    const wrapper = mount(SimpleInboundOrdersTable, {
      props: {
        stockProductCode: 'PRD-001',
      },
      global: {
        stubs: {
          SearchInput: true,
          InboundOrderStateBadge: true,
          InboundOrderGridCard: true,
        },
      },
    })

    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('IN-123')
  })
})
