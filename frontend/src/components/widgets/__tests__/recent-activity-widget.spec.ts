import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import RecentActivityWidget from '../RecentActivityWidget.vue'

installQuasarPlugin()

const mocks = vi.hoisted(() => ({
  getRecentActivity: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesAnalyticsGetRecentActivity: mocks.getRecentActivity,
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

describe('RecentActivityWidget', () => {
  beforeEach(() => {
    mocks.getRecentActivity.mockReset()
    vi.useRealTimers()
  })

  it('renders recent activity rows from api data', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-12T12:00:00Z'))

    mocks.getRecentActivity.mockResolvedValue(
      okResponse({
        data: [
          {
            id: 11,
            happened_at: '2026-05-12T11:40:00Z',
            message: 'Objednávka byla vytvořena',
            object_repr: 'OUT-001',
            actor_user: 'jonas',
            action: 'create',
          },
          {
            id: 10,
            happened_at: '2026-05-12T08:00:00Z',
            message: 'Produkt byl upraven',
            object_repr: 'PROD-001',
            actor_user: 'jonas',
            action: 'update',
          },
          {
            id: 9,
            happened_at: '2026-05-10T08:00:00Z',
            message: 'Starší auditní záznam',
            object_repr: 'OLD-001',
            actor_user: 'jonas',
            action: 'update',
          },
        ],
      }),
    )

    const wrapper = mount(RecentActivityWidget)

    await flushPromises()

    const icons = wrapper.findAll('[data-testid="activity-icon"]')
    const timestamps = wrapper.findAll('[data-testid="activity-timestamp"]')

    expect(mocks.getRecentActivity).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Objednávka byla vytvořena')
    expect(wrapper.text()).toContain('Produkt byl upraven')
    expect(icons[0]?.attributes('data-icon-name')).toBe('add')
    expect(icons[1]?.attributes('data-icon-name')).toBe('edit')
    expect(icons[2]?.attributes('data-icon-name')).toBe('edit')
    expect(wrapper.findAll('[data-testid="activity-message"]')).toHaveLength(3)
    expect(timestamps[0]?.text()).toContain('před 20min')
    expect(timestamps[1]?.text()).toContain('před 4h')
    expect(timestamps[2]?.text()).toContain(
      new Date('2026-05-10T08:00:00Z').toLocaleString('cs-CZ', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
    )
  })

  it('shows local error state when api request fails', async () => {
    mocks.getRecentActivity.mockResolvedValue(errorResponse())

    const wrapper = mount(RecentActivityWidget)

    await flushPromises()

    expect(wrapper.text()).toContain('Nepodařilo se načíst poslední aktivitu')
    expect(wrapper.text()).toContain('Server error')
  })
})
