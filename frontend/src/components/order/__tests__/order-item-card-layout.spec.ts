import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { InboundOrderItemSchema } from '@/client'
import InboundOrderProductsList from '../InboundOrderProductsList.vue'

installQuasarPlugin()

const mockViewport = (matches: boolean) =>
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  }))

const items = [
  {
    index: 0,
    amount: 2,
    unit_price: 10,
    total_price: 20,
    product: { code: 'P1', name: 'Prod', unit: 'ks' },
  },
] as unknown as InboundOrderItemSchema[]

const mountList = (list = items) =>
  mount(InboundOrderProductsList, {
    props: { items: list, currency: 'CZK', orderCode: 'K1' },
    global: {
      stubs: { RouterLink: true, InboundOrderItemEditDialog: true, ConfirmDialog: true },
    },
  })

afterEach(() => vi.unstubAllGlobals())

describe('order item list responsive layout', () => {
  it('renders cards below the breakpoint', () => {
    mockViewport(true)
    const wrapper = mountList()
    expect(wrapper.find('[data-test="order-item-cards"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-test="order-item-card"]')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Množství')
  })

  it('renders the table above the breakpoint', () => {
    mockViewport(false)
    const wrapper = mountList()
    expect(wrapper.find('[data-test="order-item-cards"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="order-item-card"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Množství')
  })

  it('shows empty state in card layout', () => {
    mockViewport(true)
    const wrapper = mountList([])
    expect(wrapper.text()).toContain('Žádné položky')
  })
})
