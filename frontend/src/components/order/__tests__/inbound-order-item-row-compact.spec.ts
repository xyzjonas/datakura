import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { InboundOrderItemSchema } from '@/client'
import CloseIconButton from '../../common/buttons/CloseIconButton.vue'
import ConfirmDialog from '../../ConfirmDialog.vue'
import InboundOrderItemRowCompact from '../InboundOrderItemRowCompact.vue'

installQuasarPlugin()

const makeItem = (unit: number, amount = 2) =>
  ({
    index: 3,
    amount,
    unit_price: unit,
    total_price: unit * amount,
    product: { code: 'P1', name: 'Prod', unit: 'KS' },
  }) as unknown as InboundOrderItemSchema

const mountRow = (item: InboundOrderItemSchema, readonly = false) =>
  mount(InboundOrderItemRowCompact, {
    props: { item, currency: 'CZK', orderCode: 'O1', readonly },
    global: {
      stubs: {
        RouterLink: true,
        InboundOrderItemEditDialog: true,
        ConfirmDialog: true,
      },
    },
  })

describe('InboundOrderItemRowCompact', () => {
  it('shows index, formatted purchase and total price', () => {
    const wrapper = mountRow(makeItem(12.5))
    expect(wrapper.text()).toContain('4')
    expect(wrapper.get('[data-test="item-purchase-price"]').text()).toContain('12.50')
    expect(wrapper.get('[data-test="item-total-price"]').text()).toContain('25.00')
  })

  it('handles zero amount', () => {
    const wrapper = mountRow(makeItem(10, 0))
    expect(wrapper.get('[data-test="item-total-price"]').text()).toContain('0.00')
  })

  it('asks for confirmation before emitting remove', async () => {
    const wrapper = mountRow(makeItem(10))
    await wrapper.findComponent(CloseIconButton).find('button').trigger('click')
    expect(wrapper.emitted('remove')).toBeUndefined()
    expect(wrapper.findComponent(ConfirmDialog).props('show')).toBe(true)
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm')
    expect(wrapper.emitted('remove')).toHaveLength(1)
  })

  it('disables edit and remove when readonly', () => {
    const wrapper = mountRow(makeItem(10), true)
    expect(
      wrapper.findComponent(CloseIconButton).find('button').attributes('disabled'),
    ).toBeDefined()
  })
})
