import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ManufacturingOrderItemSchema } from '@/client'
import ManufacturingOrderProductsList from '../ManufacturingOrderProductsList.vue'

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
    id: 7,
    index: 0,
    in_amount: 3,
    out_amount: 2,
    in_product: { code: 'IN1', name: 'Input', unit: 'ks' },
    out_product: { code: 'OUT1', name: 'Output', unit: 'kg' },
  },
] as unknown as ManufacturingOrderItemSchema[]

const mountList = (props: Record<string, unknown> = {}) =>
  mount(ManufacturingOrderProductsList, {
    props: { items, ...props },
    global: { stubs: { RouterLink: true, ConfirmDialog: true } },
  })

afterEach(() => vi.unstubAllGlobals())

describe('ManufacturingOrderProductsList', () => {
  it.each([
    [true, 'cards'],
    [false, 'table'],
  ])('renders items (cards layout: %s)', (cards) => {
    mockViewport(cards)
    const wrapper = mountList()
    expect(wrapper.find('[data-test="order-item-cards"]').exists()).toBe(cards)
    expect(wrapper.text()).toContain('IN1')
    expect(wrapper.text()).toContain('OUT1')
    expect(wrapper.find('[data-test="item-out-amount"]').text()).toContain('2')
  })

  it('shows table header and no drag handle for manufacturing items', () => {
    mockViewport(false)
    const wrapper = mountList()
    expect(wrapper.text()).toContain('Vstupní produkt')
    expect(wrapper.text()).toContain('Množství (výstup)')
    expect(wrapper.find('[draggable="true"]').exists()).toBe(false)
  })

  it.each([true, false])('renders empty state (cards layout: %s)', (cards) => {
    mockViewport(cards)
    const wrapper = mountList({ items: [] })
    expect(wrapper.text()).toContain('Žádné položky')
  })

  it('emits edit and addItem; hides add link when readonly', async () => {
    mockViewport(false)
    const wrapper = mountList({ items: [] })
    await wrapper.find('.link').trigger('click')
    expect(wrapper.emitted('addItem')).toHaveLength(1)
    const readonly = mountList({ items: [], readonly: true })
    expect(readonly.find('.link').exists()).toBe(false)
  })

  it('disables actions when readonly', () => {
    mockViewport(false)
    const wrapper = mountList({ readonly: true })
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2)
    buttons.forEach((b) => expect(b.attributes('disabled')).toBeDefined())
  })
})
