import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SellingPriceEditor from '../SellingPriceEditor.vue'

installQuasarPlugin()

describe('SellingPriceEditor', () => {
  it('shows explicit no-discount explanation in popup content', () => {
    const wrapper = mount(SellingPriceEditor, {
      props: {
        modelValue: 150,
        currency: 'CZK',
        unit: 'KS',
        basePrice: 150,
        suggestedPrice: 150,
        avgPurchasePrice: 90,
        discountPercent: 0,
        reason: 'Discount groups disabled for this product',
        priceSource: 'NO_DISCOUNT',
      },
      global: {
        stubs: {
          QPopupProxy: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain(
      'Sleva nepoužita: slevové skupiny nejsou pro tento produkt povoleny.',
    )
    expect(wrapper.text()).toContain('Discount groups disabled for this product')
  })
})
