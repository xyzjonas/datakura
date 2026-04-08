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
  it('renders customer target and emits delete', async () => {
    const row = {
      price_id: 10,
      price_type: 'CUSTOMER_DISCOUNT',
      discount_percent: 15,
      customer: {
        code: 'CUS-1',
        name: 'Customer One',
      },
      group: null,
    } as unknown as DynamicPriceRow

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

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('delete')).toEqual([[10]])
  })
})