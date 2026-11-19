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

  const mountEditor = (extra: Record<string, unknown>) =>
    mount(SellingPriceEditor, {
      props: {
        modelValue: 2,
        currency: 'EUR',
        unit: 'KS',
        basePrice: 2,
        suggestedPrice: 2,
        avgPurchasePrice: 1,
        discountPercent: 0,
        reason: 'Base',
        ...extra,
      },
      global: { stubs: { QPopupProxy: { template: '<div><slot /></div>' } } },
    })

  it('hints the price in the base currency for a foreign currency document', () => {
    const wrapper = mountEditor({ baseCurrency: 'CZK', exchangeRate: 25 })

    expect(wrapper.find('[data-test="base-price-hint"]').text()).toBe('≈ 50.00 CZK / KS')
  })

  it.each([
    { baseCurrency: 'EUR', exchangeRate: 1 }, // same currency
    {}, // not a multicurrency context
  ])('has no base currency hint for %j', (extra) => {
    const wrapper = mountEditor(extra)

    expect(wrapper.find('[data-test="base-price-hint"]').exists()).toBe(false)
  })
})
