import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { ProductSchema } from '@/client'
import ProductPricingCard from '../ProductPricingCard.vue'

const updateDynamicPriceMock = vi.fn()
const notifyMock = vi.fn()

vi.mock('@/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/client')>()
  return {
    ...actual,
    warehouseApiRoutesProductUpdateProductDynamicPrice: (...args: unknown[]) =>
      updateDynamicPriceMock(...args),
  }
})

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: unknown) => response,
  }),
}))

vi.mock('quasar', async (importOriginal) => {
  const actual = await importOriginal<typeof import('quasar')>()
  return {
    ...actual,
    useQuasar: () => ({
      notify: notifyMock,
      screen: { lt: { md: false } },
    }),
  }
})

installQuasarPlugin()

describe('ProductPricingCard', () => {
  it('updates selected dynamic price from edit dialog submit', async () => {
    const initialProduct = {
      code: 'P-100',
      base_price: 100,
      dynamic_prices: [
        {
          price_id: 7,
          fixed_price: 95,
          discount_percent: 5,
          customer: { code: 'CUS-1', name: 'Customer One' },
        },
      ],
    } as ProductSchema

    const updatedProduct = {
      ...initialProduct,
      dynamic_prices: [
        {
          price_id: 7,
          fixed_price: 90,
          discount_percent: 5,
          customer: { code: 'CUS-1', name: 'Customer One' },
        },
      ],
    } as ProductSchema

    updateDynamicPriceMock.mockResolvedValueOnce({ data: updatedProduct })

    const modelUpdates: ProductSchema[] = []

    const wrapper = mount(ProductPricingCard, {
      props: {
        modelValue: initialProduct,
        'onUpdate:modelValue': (value: ProductSchema) => {
          modelUpdates.push(value)
        },
      },
      global: {
        stubs: {
          ForegroundPanel: {
            template: '<div><slot /></div>',
          },
          ConfirmDialog: {
            template: '<div><slot /></div>',
          },
          AddDynamicPriceDialog: {
            template: '<div />',
          },
          UpdateDynamicPriceDialog: {
            template:
              '<button data-test="update-submit" @click="$emit(\'submit\', { fixed_price: 90, customer_code: \'CUS-1\' })" />',
          },
          ProductPricingGridCard: {
            template: '<div />',
          },
          QTable: {
            props: ['rows'],
            template:
              '<div><slot name="body-cell-actions" v-for="row in rows" :key="row.price_id" :row="row" :props="{ row }" /></div>',
          },
          QTd: {
            template: '<div><slot /></div>',
          },
          QBtn: {
            props: ['icon'],
            template: '<button :data-icon="icon" @click="$emit(\'click\')"><slot /></button>',
          },
          QTooltip: {
            template: '<span><slot /></span>',
          },
          'router-link': {
            template: '<a><slot /></a>',
          },
        },
      },
    })

    await wrapper.find('button[data-icon="sym_o_edit"]').trigger('click')
    await wrapper.find('[data-test="update-submit"]').trigger('click')

    expect(updateDynamicPriceMock).toHaveBeenCalledWith({
      path: { product_code: 'P-100', price_id: 7 },
      body: { fixed_price: 90, customer_code: 'CUS-1' },
    })
    expect(modelUpdates.at(-1)).toEqual(updatedProduct)
  })
})
