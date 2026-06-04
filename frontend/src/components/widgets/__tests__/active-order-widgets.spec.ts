import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ActiveOrdersWidget from '../ActiveOrdersWidget.vue'
import ActiveWarehouseOrdersWidget from '../ActiveWarehouseOrdersWidget.vue'

installQuasarPlugin()

const mocks = vi.hoisted(() => ({
  getRecentOrdersActivity: vi.fn(),
  getRecentOrders: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesAnalyticsGetRecentOrdersActivity: mocks.getRecentOrdersActivity,
  warehouseApiRoutesAnalyticsGetRecentOrders: mocks.getRecentOrders,
}))

const okResponse = <T>(data: T) => ({
  data,
  response: {
    ok: true,
    statusText: 'OK',
  },
})

const errorResponse = (statusText = 'Server error') => ({
  data: undefined,
  response: {
    ok: false,
    statusText,
  },
})

const mountWithGraphStub = (component: object) => {
  return mount(component, {
    global: {
      stubs: {
        DemoGraphWidget: {
          props: ['title', 'caption', 'subtitle', 'data', 'series', 'to'],
          template:
            '<div data-testid="graph">{{ title }}|{{ caption }}|{{ subtitle }}|{{ JSON.stringify(data) }}|{{ JSON.stringify(series) }}|{{ JSON.stringify(to) }}</div>',
        },
      },
    },
  })
}

describe('active dashboard order widgets', () => {
  beforeEach(() => {
    mocks.getRecentOrdersActivity.mockReset()
    mocks.getRecentOrders.mockReset()
  })

  it('plots inbound and outbound recent orders in a single graph with combined total as title', async () => {
    mocks.getRecentOrdersActivity.mockResolvedValue(
      okResponse({
        data: {
          days: 3,
          inbound: [
            { date: '2026-06-02', value: 3 },
            { date: '2026-06-03', value: 1 },
            { date: '2026-06-04', value: 5 },
          ],
          outbound: [
            { date: '2026-06-02', value: 2 },
            { date: '2026-06-03', value: 4 },
            { date: '2026-06-04', value: 6 },
          ],
        },
      }),
    )

    const wrapper = mountWithGraphStub(ActiveOrdersWidget)

    await flushPromises()

    expect(mocks.getRecentOrdersActivity).toHaveBeenCalledWith({
      query: { days: 14 },
    })

    const graph = wrapper.get('[data-testid="graph"]')
    const graphText = graph.text()

    expect(graphText).toContain('11')
    expect(graphText).toContain('vydané 9 / přijaté 12')
    expect(graphText).toContain('Vydané objednávky')
    expect(graphText).toContain('Přijaté objednávky')
    expect(graphText).toContain('orders')
  })

  it('shows local error when recent orders activity fetch fails', async () => {
    mocks.getRecentOrdersActivity.mockResolvedValue(errorResponse('Activity broken'))

    const wrapper = mountWithGraphStub(ActiveOrdersWidget)

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst aktivní objednávky')
    expect(wrapper.text()).toContain('Activity broken')
  })

  it('plots inbound and outbound recent warehouse orders in a single graph with combined total as title', async () => {
    mocks.getRecentOrders.mockResolvedValue(
      okResponse({
        data: {
          days: 3,
          inbound: [
            { date: '2026-06-02', value: 1 },
            { date: '2026-06-03', value: 4 },
            { date: '2026-06-04', value: 2 },
          ],
          outbound: [
            { date: '2026-06-02', value: 0 },
            { date: '2026-06-03', value: 5 },
            { date: '2026-06-04', value: 7 },
          ],
        },
      }),
    )

    const wrapper = mountWithGraphStub(ActiveWarehouseOrdersWidget)

    await flushPromises()

    expect(mocks.getRecentOrders).toHaveBeenCalledWith({
      query: { days: 14 },
    })

    const graph = wrapper.get('[data-testid="graph"]')
    const graphText = graph.text()

    expect(graphText).toContain('9')
    expect(graphText).toContain('příjemky 7 / výdejky 12')
    expect(graphText).toContain('Příjemky')
    expect(graphText).toContain('Výdejky')
    expect(graphText).toContain('warehouseInboundOrders')
  })

  it('shows local error when recent orders fetch fails', async () => {
    mocks.getRecentOrders.mockResolvedValue(errorResponse('Recent broken'))

    const wrapper = mountWithGraphStub(ActiveWarehouseOrdersWidget)

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst aktivní skladové doklady')
    expect(wrapper.text()).toContain('Recent broken')
  })
})
