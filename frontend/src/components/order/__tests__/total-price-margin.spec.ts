import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TotalPrice from '../TotalPrice.vue'
import ItemMarginSummary from '../ItemMarginSummary.vue'

installQuasarPlugin()

const pricing = (avg: number) => ({ avg_purchase_price: avg })

describe('TotalPrice margin', () => {
  it('shows green margin on gain', () => {
    const wrapper = mount(TotalPrice, {
      props: {
        order: {
          currency: 'CZK',
          items: [{ amount: 2, unit_price: 100, pricing_details: pricing(60) }],
        },
      },
    })
    const margin = wrapper.get('[data-test="order-margin"]')
    expect(margin.text()).toContain('+80.00')
    expect(margin.find('.text-green-600').exists()).toBe(true)
  })

  it('shows red margin on loss', () => {
    const wrapper = mount(TotalPrice, {
      props: {
        order: {
          currency: 'CZK',
          items: [{ amount: 1, unit_price: 50, pricing_details: pricing(80) }],
        },
      },
    })
    expect(wrapper.get('[data-test="order-margin"]').find('.text-red').exists()).toBe(true)
  })

  it('hides margin when items carry no pricing details', () => {
    const wrapper = mount(TotalPrice, {
      props: { order: { currency: 'CZK', items: [{ amount: 1, unit_price: 50 }] } },
    })
    expect(wrapper.find('[data-test="order-margin"]').exists()).toBe(false)
  })
})

describe('ItemMarginSummary', () => {
  it('shows purchase value and margin', () => {
    const wrapper = mount(ItemMarginSummary, {
      props: { currency: 'CZK', amount: 3, purchasePrice: 10, totalPrice: 24 },
    })
    expect(wrapper.text()).toContain('Skladová hodnota: 30.00 CZK')
    expect(wrapper.text()).toContain('-6.00')
    expect(wrapper.find('.text-red').exists()).toBe(true)
  })
})
