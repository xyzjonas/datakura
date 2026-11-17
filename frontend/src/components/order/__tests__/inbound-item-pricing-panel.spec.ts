import type { ProductSchema } from '@/client'
import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { Notify } from 'quasar'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InboundItemPricingPanel from '../InboundItemPricingPanel.vue'

installQuasarPlugin({ plugins: { Notify } })

const { updateBasePrice, onResponse } = vi.hoisted(() => ({
  updateBasePrice: vi.fn(),
  onResponse: vi.fn((res: unknown) => res),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesProductUpdateProductBasePrice: updateBasePrice,
  warehouseApiRoutesSettingsGetGlobalSettings: vi.fn().mockResolvedValue({}),
}))
vi.mock('@/composables/use-api', () => ({ useApi: () => ({ onResponse }) }))

const makeProduct = (overrides: Partial<ProductSchema> = {}) =>
  ({
    code: 'P1',
    name: 'Product',
    unit: 'KS',
    base_price: 150,
    purchase_price: 100,
    currency: 'CZK',
    ...overrides,
  }) as ProductSchema

const mountIt = (newPurchasePrice: number, product: ProductSchema | null = makeProduct()) =>
  mount(InboundItemPricingPanel, {
    props: {
      currency: 'CZK',
      newPurchasePrice,
      product: product ?? undefined,
      'onUpdate:product': (value: ProductSchema | undefined) => wrapperProps.set('product', value),
    },
  })
const wrapperProps = new Map<string, unknown>()

beforeEach(() => {
  vi.clearAllMocks()
  wrapperProps.clear()
})

describe('InboundItemPricingPanel', () => {
  it('shows current and new purchase price with percentage and raw delta', () => {
    const wrapper = mountIt(110)

    expect(wrapper.get('[data-test="purchase-current"]').text()).toBe('100.00')
    expect(wrapper.get('[data-test="purchase-new"]').text()).toContain('110.00')
    const deltaText = wrapper.get('[data-test="purchase-delta-values"]').text()
    expect(deltaText).toContain('+10.0 %')
    expect(deltaText).toContain('+10.00 CZK')
    expect(wrapper.get('[data-test="purchase-delta-values"]').classes()).toContain('text-negative')
  })

  it('marks a cheaper purchase as good news', () => {
    const wrapper = mountIt(90)

    expect(wrapper.get('[data-test="purchase-delta-values"]').text()).toContain('-10.0 %')
    expect(wrapper.get('[data-test="purchase-delta-values"]').classes()).toContain('text-positive')
  })

  it('omits the percentage when there is no current purchase price', () => {
    const wrapper = mountIt(50, makeProduct({ purchase_price: 0 }))

    const deltaText = wrapper.get('[data-test="purchase-delta-values"]').text()
    expect(deltaText).not.toContain('%')
    expect(deltaText).toContain('+50.00 CZK')
  })

  it('computes margin and markup of the base price against the NEW purchase price', () => {
    // sell 150, buy 110 -> profit 40 = 26.7 % margin, 36.4 % markup
    const wrapper = mountIt(110)

    expect(wrapper.get('[data-test="impact-margin"]').text()).toBe('+26.7%')
    expect(wrapper.get('[data-test="impact-markup"]').text()).toBe('+36.4%')
    // ...and shows what it used to be: sell 150, buy 100 -> 33.3 % / 50.0 %
    expect(wrapper.get('[data-test="impact"]').text()).toContain('nyní +33.3%')
    expect(wrapper.get('[data-test="impact"]').text()).toContain('nyní +50.0%')
  })

  it('recomputes the impact live when the base price is edited', async () => {
    const wrapper = mountIt(110)

    await wrapper.get('input[data-test="base-price-input"]').setValue('165')

    // sell 165, buy 110 -> 55 = 33.3 % margin, 50 % markup
    expect(wrapper.get('[data-test="impact-margin"]').text()).toBe('+33.3%')
    expect(wrapper.get('[data-test="impact-markup"]').text()).toBe('+50.0%')
  })

  it('shows a loss when selling below the new purchase price', async () => {
    const wrapper = mountIt(200)

    expect(wrapper.get('[data-test="impact-margin"]').text()).toBe('-33.3%')
    expect(wrapper.get('[data-test="impact-margin"]').classes()).toContain('text-red')
  })

  it('offers saving only when the base price differs from the current one', async () => {
    const wrapper = mountIt(110)
    expect(wrapper.find('[data-test="base-price-save"]').exists()).toBe(false)

    const input = wrapper.get('input[data-test="base-price-input"]')
    await input.setValue('165')
    expect(wrapper.find('[data-test="base-price-save"]').exists()).toBe(true)

    await input.setValue('150')
    expect(wrapper.find('[data-test="base-price-save"]').exists()).toBe(false)
  })

  it.each(['', '-5'])('does not offer saving an invalid price (%j)', async (value) => {
    const wrapper = mountIt(110)

    await wrapper.get('input[data-test="base-price-input"]').setValue(value)

    expect(wrapper.find('[data-test="base-price-save"]').exists()).toBe(false)
  })

  it('stores the new base price and hands the updated product back', async () => {
    const saved = makeProduct({ base_price: 165 })
    updateBasePrice.mockResolvedValue({ data: saved })
    const wrapper = mountIt(110)

    await wrapper.get('input[data-test="base-price-input"]').setValue('165')
    await wrapper.get('[data-test="base-price-save"]').trigger('click')
    await flushPromises()

    expect(updateBasePrice).toHaveBeenCalledWith({
      path: { product_code: 'P1' },
      body: { base_price: 165 },
    })
    expect(wrapper.emitted('update:product')!.at(-1)).toEqual([saved])
  })

  it('keeps the draft when saving fails', async () => {
    updateBasePrice.mockResolvedValue({ error: 'boom' })
    onResponse.mockReturnValueOnce(undefined)
    const wrapper = mountIt(110)

    await wrapper.get('input[data-test="base-price-input"]').setValue('165')
    await wrapper.get('[data-test="base-price-save"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('update:product')).toBeUndefined()
    expect(wrapper.find('[data-test="base-price-save"]').exists()).toBe(true)
  })

  it('renders nothing without a product', () => {
    const wrapper = mountIt(10, null)

    expect(wrapper.find('[data-test="pricing-panel"]').exists()).toBe(false)
  })
})
