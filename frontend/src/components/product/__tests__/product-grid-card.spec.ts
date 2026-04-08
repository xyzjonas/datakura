import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { ProductSchema } from '@/client'
import ProductGridCard from '../ProductGridCard.vue'

installQuasarPlugin()

describe('ProductGridCard', () => {
  it('renders product details and routes to product detail on click', async () => {
    const push = vi.fn()
    const product = {
      name: 'Test Product',
      code: 'PRD-001',
      type: 'Zboží',
      group: 'Electronics',
      purchase_price: 125,
      base_price: 199,
      currency: 'CZK',
    } as unknown as ProductSchema

    const wrapper = mount(ProductGridCard, {
      props: { product },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          ProductTypeIcon: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Test Product')
    expect(wrapper.text()).toContain('PRD-001')
    expect(wrapper.text()).toContain('Electronics')
    expect(wrapper.text()).toContain('125 CZK')
    expect(wrapper.text()).toContain('199 CZK')

    await wrapper.find('a.link').trigger('click')

    expect(push).toHaveBeenCalledWith({
      name: 'productDetail',
      params: { productCode: 'PRD-001' },
    })
  })
})
