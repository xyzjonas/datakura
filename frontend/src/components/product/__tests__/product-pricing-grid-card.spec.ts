import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { DynamicProductPriceSchema } from '@/client'
import ProductPricingGridCard from '../ProductPricingGridCard.vue'

installQuasarPlugin()

type DynamicPriceRow = DynamicProductPriceSchema & {
  customer?: { code: string; name: string } | null
}

describe('ProductPricingGridCard', () => {
  it('renders customer target and emits edit and delete', async () => {
    const row = {
      price_id: 10,
      fixed_price: 170,
      discount_percent: 15,
      customer: {
        code: 'CUS-1',
        name: 'Customer One',
      },
    } as DynamicPriceRow

    const wrapper = mount(ProductPricingGridCard, {
      props: {
        row,
        priceTypeLabel: 'Sleva pro zákazníka',
        finalPrice: 170,
        deletingPriceId: null,
      },
      global: {
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Sleva pro zákazníka')
    expect(wrapper.text()).toContain('Zákazník: CUS-1')
    expect(wrapper.text()).toContain('170 Kč')
    expect(wrapper.text()).toContain('Customer One')

    const actionButtons = wrapper.findAll('button')
    expect(actionButtons).toHaveLength(2)

    await actionButtons[0].trigger('click')
    expect(wrapper.emitted('edit')).toEqual([[10]])

    await actionButtons[1].trigger('click')
    expect(wrapper.emitted('delete')).toEqual([[10]])
  })
})
