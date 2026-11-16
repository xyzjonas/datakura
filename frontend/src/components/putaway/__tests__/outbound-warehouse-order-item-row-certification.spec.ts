import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { OutboundWarehouseOrderItemSchema } from '@/client'
import OutboundWarehouseOrderItemRow from '../OutboundWarehouseOrderItemRow.vue'

installQuasarPlugin()

const item = (patch: Partial<OutboundWarehouseOrderItemSchema>) =>
  ({
    id: 1,
    amount: '2',
    unit_of_measure: 'ks',
    pending: true,
    index: 0,
    product: { name: 'Matice', code: 'P1', unit: 'ks' },
    desired_package_type_name: null,
    desired_batch_code: 'B-1',
    required_origin_country: null,
    ...patch,
  }) as unknown as OutboundWarehouseOrderItemSchema

const mountIt = (i: OutboundWarehouseOrderItemSchema) =>
  mount(OutboundWarehouseOrderItemRow, {
    props: { index: 0, item: i, warehouseOrderCode: 'W1' },
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        OutboundWarehousePickDialog: true,
        WarehouseItemAmountBadge: true,
        CountryBadge: true,
        IndexRectangle: true,
      },
    },
  })

describe('OutboundWarehouseOrderItemRow - certification', () => {
  it('tells the worker a certified batch has to be picked', () => {
    const wrapper = mountIt(item({ desired_batch_certification: { id: 1, code: 'ISO-9001' } }))

    expect(wrapper.find('[data-test="certification-badge"]').text()).toContain('ISO-9001')
  })

  it('shows no certification for a plain batch', () => {
    const wrapper = mountIt(item({ desired_batch_certification: null }))

    expect(wrapper.find('[data-test="certification-badge"]').exists()).toBe(false)
  })
})
