import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ActiveOrdersWidget from '../ActiveOrdersWidget.vue'
import ActiveWarehouseOrdersWidget from '../ActiveWarehouseOrdersWidget.vue'

installQuasarPlugin()

const mocks = vi.hoisted(() => ({
  getInboundOrders: vi.fn(),
  getOutboundOrders: vi.fn(),
  getInboundWarehouseOrders: vi.fn(),
  getOutboundWarehouseOrders: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesInboundOrdersGetInboundOrders: mocks.getInboundOrders,
  warehouseApiRoutesOutboundOrdersGetOutboundOrders: mocks.getOutboundOrders,
  warehouseApiRoutesWarehouseGetInboundWarehouseOrders: mocks.getInboundWarehouseOrders,
  warehouseApiRoutesWarehouseGetOutboundWarehouseOrders: mocks.getOutboundWarehouseOrders,
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

const mountWithSingleValueStub = (component: object) => {
  return mount(component, {
    global: {
      stubs: {
        SingleValueWidget: {
          props: ['title', 'subtitle', 'to'],
          template:
            '<div data-testid="widget">{{ title }}|{{ subtitle }}|{{ JSON.stringify(to) }}</div>',
        },
      },
    },
  })
}

describe('active dashboard order widgets', () => {
  beforeEach(() => {
    mocks.getInboundOrders.mockReset()
    mocks.getOutboundOrders.mockReset()
    mocks.getInboundWarehouseOrders.mockReset()
    mocks.getOutboundWarehouseOrders.mockReset()
  })

  it('shows loading then aggregated active order counts', async () => {
    let releaseInbound: (() => void) | undefined
    const inboundPromise = new Promise((resolve) => {
      releaseInbound = () =>
        resolve(
          okResponse({
            data: [
              {
                code: 'IN-1',
                state: 'draft',
              },
            ],
            count: 3,
          }),
        )
    })

    mocks.getInboundOrders.mockReturnValueOnce(inboundPromise)
    mocks.getOutboundOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'OUT-1',
            state: 'submitted',
          },
        ],
        count: 2,
      }),
    )
    mocks.getOutboundOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'OUT-1',
            state: 'submitted',
          },
          {
            code: 'OUT-2',
            state: 'completed_paid',
          },
        ],
        count: 2,
      }),
    )

    const wrapper = mountWithSingleValueStub(ActiveOrdersWidget)

    expect(wrapper.get('[data-testid="widget"]').text()).toContain('Načítám aktivní objednávky')

    releaseInbound?.()

    mocks.getInboundOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'IN-1',
            state: 'draft',
          },
          {
            code: 'IN-2',
            state: 'completed',
          },
          {
            code: 'IN-3',
            state: 'cancelled',
          },
        ],
        count: 3,
      }),
    )

    await flushPromises()

    const widgetText = wrapper.get('[data-testid="widget"]').text()

    expect(widgetText).toContain('2')
    expect(widgetText).toContain('vydané 1 / přijaté 1')
    expect(widgetText).toContain('orders')
    expect(mocks.getInboundOrders).toHaveBeenNthCalledWith(1, {
      query: {
        page: 1,
        page_size: 1,
      },
    })
    expect(mocks.getInboundOrders).toHaveBeenNthCalledWith(2, {
      query: {
        page: 1,
        page_size: 3,
      },
    })
    expect(mocks.getOutboundOrders).toHaveBeenNthCalledWith(1, {
      query: {
        page: 1,
        page_size: 1,
      },
    })
    expect(mocks.getOutboundOrders).toHaveBeenNthCalledWith(2, {
      query: {
        page: 1,
        page_size: 2,
      },
    })
  })

  it('shows local error when active orders fetch fails', async () => {
    mocks.getInboundOrders.mockResolvedValue(errorResponse('Inbound broken'))
    mocks.getOutboundOrders.mockResolvedValue(
      okResponse({
        data: [],
        count: 0,
      }),
    )

    const wrapper = mountWithSingleValueStub(ActiveOrdersWidget)

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst aktivní objednávky')
    expect(wrapper.text()).toContain('Inbound broken')
  })

  it('shows aggregated active warehouse order counts', async () => {
    mocks.getInboundWarehouseOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'WI-1',
            state: 'pending',
          },
        ],
        count: 2,
      }),
    )
    mocks.getInboundWarehouseOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'WI-1',
            state: 'pending',
          },
          {
            code: 'WI-2',
            state: 'completed',
          },
        ],
        count: 2,
      }),
    )
    mocks.getOutboundWarehouseOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'WO-1',
            state: 'started',
          },
        ],
        count: 2,
      }),
    )
    mocks.getOutboundWarehouseOrders.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            code: 'WO-1',
            state: 'started',
          },
          {
            code: 'WO-2',
            state: 'cancelled',
          },
        ],
        count: 2,
      }),
    )

    const wrapper = mountWithSingleValueStub(ActiveWarehouseOrdersWidget)

    await flushPromises()

    const widgetText = wrapper.get('[data-testid="widget"]').text()

    expect(widgetText).toContain('2')
    expect(widgetText).toContain('příjemky 1 / výdejky 1')
    expect(widgetText).toContain('warehouseInboundOrders')
  })

  it('shows local error when warehouse order fetch fails', async () => {
    mocks.getInboundWarehouseOrders.mockResolvedValue(
      okResponse({
        data: [],
        count: 0,
      }),
    )
    mocks.getOutboundWarehouseOrders.mockResolvedValue(errorResponse('Warehouse broken'))

    const wrapper = mountWithSingleValueStub(ActiveWarehouseOrdersWidget)

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst aktivní skladové doklady')
    expect(wrapper.text()).toContain('Warehouse broken')
  })
})
