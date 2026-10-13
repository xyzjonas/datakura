import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { OutboundOrderItemSchema } from '@/client'
import OutboundOrderItemRowCompact from '../OutboundOrderItemRowCompact.vue'
import ConfirmDialog from '../../ConfirmDialog.vue'
import CloseIconButton from '../../common/buttons/CloseIconButton.vue'

installQuasarPlugin()

const makeItem = (unit: number, purchase: number, amount = 2) =>
  ({
    index: 0,
    amount,
    unit_price: unit,
    total_price: unit * amount,
    product: { code: 'P1', name: 'Prod', unit: 'KS', base_price: unit, purchase_price: purchase },
    pricing_details: {
      base_price: unit,
      avg_purchase_price: purchase,
      suggested_unit_price: unit,
      selected_unit_price: unit,
      discount_percent: 0,
      reason: 'Base',
      source: 'BASE_PRICE',
      margin_amount: unit - purchase,
      margin_percent: 0,
    },
  }) as unknown as OutboundOrderItemSchema

const mountRow = (item: OutboundOrderItemSchema) =>
  mount(OutboundOrderItemRowCompact, {
    props: { item, currency: 'CZK', orderCode: 'K1', readonly: true },
    global: {
      stubs: {
        RouterLink: true,
        ProductAvailability: true,
        OutboundOrderItemEditDialog: true,
        QPopupProxy: true,
      },
    },
  })

describe('OutboundOrderItemRowCompact remove', () => {
  const mountEditable = () =>
    mount(OutboundOrderItemRowCompact, {
      props: { item: makeItem(100, 60), currency: 'CZK', orderCode: 'K1' },
      global: {
        stubs: {
          RouterLink: true,
          ProductAvailability: true,
          OutboundOrderItemEditDialog: true,
          QPopupProxy: true,
          ConfirmDialog: true,
        },
      },
    })

  it('does not emit remove on delete click, opens confirmation instead', async () => {
    const wrapper = mountEditable()
    await wrapper.findComponent(CloseIconButton).find('button').trigger('click')
    expect(wrapper.emitted('remove')).toBeUndefined()
    expect(wrapper.findComponent(ConfirmDialog).props('show')).toBe(true)
  })

  it('emits remove only after confirmation', async () => {
    const wrapper = mountEditable()
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm')
    expect(wrapper.emitted('remove')).toHaveLength(1)
  })
})

describe('OutboundOrderItemRowCompact margin', () => {
  it('shows purchase price and green margin on gain', () => {
    const wrapper = mountRow(makeItem(100, 60))
    expect(wrapper.get('[data-test="item-purchase-price"]').text()).toContain('60.00')
    const margin = wrapper.get('[data-test="item-margin"]')
    expect(margin.text()).toContain('+80.00')
    expect(margin.text()).toContain('+66.7%')
    expect(margin.find('.text-green-600').exists()).toBe(true)
  })

  it('shows red margin on loss', () => {
    const wrapper = mountRow(makeItem(50, 80))
    const margin = wrapper.get('[data-test="item-margin"]')
    expect(margin.text()).toContain('-60.00')
    expect(margin.find('.text-red').exists()).toBe(true)
  })

  it('shows highlighted unit price', () => {
    const text = mountRow(makeItem(100, 60)).get('[data-test="item-unit-price"]').text()
    expect(text).toContain('100.00')
    expect(text).toContain('CZK')
  })
})
