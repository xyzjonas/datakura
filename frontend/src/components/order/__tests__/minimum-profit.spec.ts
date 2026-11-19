import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import type { OutboundOrderItemSchema } from '@/client'
import { setMinimumMarkupPercent } from '@/composables/use-minimum-profit'
import MinimumProfitBanner from '../MinimumProfitBanner.vue'
import OrderTotalsHeader from '../OrderTotalsHeader.vue'
import OutboundOrderItemRowCompact from '../OutboundOrderItemRowCompact.vue'

installQuasarPlugin()

afterEach(() => setMinimumMarkupPercent(0))

const makeItem = (unit: number, purchase: number) =>
  ({
    index: 0,
    amount: 1,
    unit_price: unit,
    total_price: unit,
    document_unit_price: unit,
    document_total_price: unit,
    product: { code: 'P1', name: 'Prod', unit: 'KS', base_price: unit, purchase_price: purchase },
    pricing_details: { avg_purchase_price: purchase },
  }) as unknown as OutboundOrderItemSchema

const mountRow = (item: OutboundOrderItemSchema) =>
  mount(OutboundOrderItemRowCompact, {
    props: {
      item,
      currency: 'CZK',
      baseCurrency: 'CZK',
      exchangeRate: 1,
      orderCode: 'K1',
      readonly: true,
    },
    global: {
      stubs: {
        RouterLink: true,
        ProductAvailability: true,
        OutboundOrderItemEditDialog: true,
        QPopupProxy: true,
      },
    },
  })

describe('item row profit guard', () => {
  it('highlights an item below the minimum markup, even if still profitable', () => {
    setMinimumMarkupPercent(30)
    const wrapper = mountRow(makeItem(110, 100)) // +10 % markup
    expect(wrapper.find('[data-test="below-minimum-profit"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="item-margin"]').find('.text-red').exists()).toBe(true)
    expect(wrapper.get('[data-test="item-margin"]').find('.text-green-600').exists()).toBe(false)
  })

  it.each([
    ['item above the minimum', 30, 140, 100],
    ['guard turned off', 0, 90, 100],
  ])('does not highlight: %s', (_, min, unit, purchase) => {
    setMinimumMarkupPercent(min)
    const wrapper = mountRow(makeItem(unit, purchase))
    expect(wrapper.find('[data-test="below-minimum-profit"]').exists()).toBe(false)
  })
})

describe('order totals profit guard', () => {
  const order = (unit: number, purchase: number) => ({
    currency: 'CZK',
    items: [{ amount: 1, unit_price: unit, pricing_details: { avg_purchase_price: purchase } }],
  })

  it('turns marže, přirážka and zisk red below the minimum', () => {
    setMinimumMarkupPercent(30)
    const wrapper = mount(OrderTotalsHeader, { props: { order: order(110, 100) as never } })
    for (const test of ['order-margin-percent', 'order-markup-percent', 'order-profit']) {
      expect(wrapper.get(`[data-test="${test}"]`).find('.text-red').exists()).toBe(true)
    }
  })

  it('stays green above the minimum', () => {
    setMinimumMarkupPercent(30)
    const wrapper = mount(OrderTotalsHeader, { props: { order: order(140, 100) as never } })
    expect(wrapper.get('[data-test="order-profit"]').find('.text-green').exists()).toBe(true)
  })
})

describe('MinimumProfitBanner', () => {
  const mountBanner = (props: { itemCount: number; orderBelow: boolean }) =>
    mount(MinimumProfitBanner, {
      props: { ...props, minimumMarkupPercent: 25, documentLabel: 'nabídky' },
    })

  it('is hidden when nothing is below the minimum', () => {
    expect(
      mountBanner({ itemCount: 0, orderBelow: false })
        .find('[data-test="minimum-profit-banner"]')
        .exists(),
    ).toBe(false)
  })

  it('explains the threshold in both přirážka and marže', () => {
    const text = mountBanner({ itemCount: 2, orderBelow: false }).text()
    expect(text).toContain('přirážka 25 %')
    expect(text).toContain('marže 20 %')
    expect(text).toContain('2 položek')
  })

  it('mentions the whole document', () => {
    const wrapper = mountBanner({ itemCount: 0, orderBelow: true })
    expect(wrapper.find('[data-test="minimum-profit-items"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="minimum-profit-order"]').text()).toContain('nabídky')
  })
})
