import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import WarehouseValueWidget from '../WarehouseValueWidget.vue'

installQuasarPlugin()

const mocks = vi.hoisted(() => ({
  getInventorySnapshots: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesAnalyticsGetInventorySnapshots: mocks.getInventorySnapshots,
}))

const okResponse = (data: unknown) => ({
  data,
  response: {
    ok: true,
    statusText: 'OK',
  },
})

const errorResponse = () => ({
  data: undefined,
  response: {
    ok: false,
    statusText: 'Server error',
  },
})

describe('WarehouseValueWidget', () => {
  beforeEach(() => {
    mocks.getInventorySnapshots.mockReset()
  })

  it('loads latest warehouse value and chart data from snapshots', async () => {
    vi.useFakeTimers()

    mocks.getInventorySnapshots.mockResolvedValue(
      okResponse({
        data: [
          {
            id: 11,
            created: '2026-04-30T10:00:00Z',
            changed: '2026-04-30T10:00:00Z',
            captured_at: '2026-04-30T10:00:00Z',
            trigger_source: 'manual',
            cadence: null,
            bucket_key: null,
            line_count: 12,
            purchase_totals: [{ currency: 'CZK', value: '150.0000' }],
            receipt_totals: [{ currency: 'CZK', value: '120.0000' }],
            receipt_unpriced_line_count: 0,
            receipt_complete: true,
          },
          {
            id: 10,
            created: '2026-04-29T10:00:00Z',
            changed: '2026-04-29T10:00:00Z',
            captured_at: '2026-04-29T10:00:00Z',
            trigger_source: 'manual',
            cadence: null,
            bucket_key: null,
            line_count: 10,
            purchase_totals: [{ currency: 'CZK', value: '125.5000' }],
            receipt_totals: [{ currency: 'CZK', value: '99.0000' }],
            receipt_unpriced_line_count: 0,
            receipt_complete: true,
          },
        ],
      }),
    )

    const wrapper = mount(WarehouseValueWidget, {
      global: {
        stubs: {
          DemoGraphWidget: {
            props: ['title', 'subtitle', 'data', 'to'],
            template:
              '<div data-testid="widget">{{ title }}|{{ subtitle }}|{{ JSON.stringify(data) }}|{{ JSON.stringify(to) }}</div>',
          },
        },
      },
    })

    await flushPromises()
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(mocks.getInventorySnapshots).toHaveBeenCalledWith({
      query: {
        page: 1,
        page_size: 10,
      },
    })
    const widgetText = wrapper.get('[data-testid="widget"]').text()

    expect(widgetText).toContain('150,00')
    expect(widgetText).toContain('Kč')
    expect(widgetText).toContain('Aktuální hodnota skladu')
    expect(widgetText).toContain('125.5')
    expect(widgetText).toContain('150')
    expect(widgetText).toContain('inventorySnapshots')

    vi.useRealTimers()
  })

  it('shows a local error state when snapshot fetch fails', async () => {
    mocks.getInventorySnapshots.mockResolvedValue(errorResponse())

    const wrapper = mount(WarehouseValueWidget, {
      global: {
        stubs: {
          DemoGraphWidget: {
            props: ['title', 'subtitle'],
            template: '<div>{{ title }}|{{ subtitle }}</div>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst hodnotu skladu')
    expect(wrapper.text()).toContain('Server error')
  })
})
