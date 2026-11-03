import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OrderTotalsHeader from '../OrderTotalsHeader.vue'

installQuasarPlugin()

const pricing = (avg: number) => ({ avg_purchase_price: avg })

const mountHeader = (order: object) =>
  mount(OrderTotalsHeader, { props: { order: order as never } })

describe('OrderTotalsHeader', () => {
  it('shows marže (of selling), přirážka (of purchase) and zisk', () => {
    // buy 70, sell 100 -> zisk 30, marže 30 %, přirážka 42.9 %
    const wrapper = mountHeader({
      currency: 'CZK',
      items: [{ amount: 1, unit_price: 100, pricing_details: pricing(70) }],
    })
    expect(wrapper.get('[data-test="order-margin-percent"]').text()).toContain('+30%')
    expect(wrapper.get('[data-test="order-markup-percent"]').text()).toContain('+42.86%')
    const profit = wrapper.get('[data-test="order-profit"]')
    expect(profit.text()).toContain('+30')
    expect(profit.text()).toContain('CZK')
    expect(profit.find('.text-green').exists()).toBe(true)
  })

  it('shows negative numbers in red on loss', () => {
    const wrapper = mountHeader({
      currency: 'CZK',
      items: [{ amount: 1, unit_price: 50, pricing_details: pricing(80) }],
    })
    expect(wrapper.get('[data-test="order-margin-percent"]').text()).toContain('-60%')
    expect(wrapper.get('[data-test="order-profit"]').find('.text-red').exists()).toBe(true)
  })

  it('shows dashes when items carry no pricing details (e.g. other order type)', () => {
    const wrapper = mountHeader({ currency: 'EUR', items: [{ amount: 3, unit_price: 5 }] })
    expect(wrapper.get('[data-test="order-margin-percent"]').text()).toContain('–')
    expect(wrapper.get('[data-test="order-markup-percent"]').text()).toContain('–')
    expect(wrapper.text()).toContain('15')
  })
})

describe('OrderTotalsHeader without margin (inbound)', () => {
  const mountInbound = (items: object[]) =>
    mount(OrderTotalsHeader, {
      props: { order: { currency: 'CZK', items } as never, showMargin: false },
    })

  it('hides selling-side and margin cards, keeps purchase total and weight', () => {
    const wrapper = mountInbound([{ amount: 3, unit_price: 5, product: { unit_weight: 2 } }])
    expect(wrapper.find('[data-test="order-margin-percent"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="order-markup-percent"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="order-profit"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Hodnota ve skladové ceně')
    expect(wrapper.text()).toContain('Celková nákupní cena')
    expect(wrapper.text()).toContain('15')
    expect(wrapper.text()).toContain('6.00')
  })

  it('handles an order without items', () => {
    const wrapper = mountInbound([])
    expect(wrapper.text()).toContain('0.00')
  })
})
