import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { WarehouseItemSchema } from '@/client'
import type { WarehouseItemSchemaWithCount } from '@/utils/aggregatePackaging'
import WarehouseItemGridCard from '../WarehouseItemGridCard.vue'

installQuasarPlugin()

describe('WarehouseItemGridCard', () => {
  it('renders non-aggregate view and routes by EAN click', async () => {
    const push = vi.fn()
    const item = {
      id: 42,
      tracking_level: 'SERIALIZED_PACKAGE',
      primary_barcode: 'EAN-001',
      amount: 8,
      package: {
        type: 'BOX',
        amount: 10,
      },
    } as unknown as WarehouseItemSchema

    const wrapper = mount(WarehouseItemGridCard, {
      props: {
        item,
        aggregate: false,
      },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          TrackingLevelBadge: true,
          PackageTypeBadge: true,
          WarehouseItemCountBadge: true,
        },
      },
    })

    expect(wrapper.text()).toContain('EAN-001')
    await wrapper.find('a.link').trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'warehouseItemDetail',
      params: { itemId: 42 },
    })
  })

  it('renders aggregate fields when aggregate is enabled', () => {
    const item = {
      id: 84,
      tracking_level: 'SERIALIZED_PACKAGE',
      amount: 25,
      itemsCount: 3,
      unit_of_measure: 'KS',
      package: {
        type: 'BOX',
        amount: 12,
      },
    } as unknown as WarehouseItemSchemaWithCount

    const wrapper = mount(WarehouseItemGridCard, {
      props: {
        item,
        aggregate: true,
      },
      global: {
        stubs: {
          TrackingLevelBadge: true,
          PackageTypeBadge: true,
          WarehouseItemCountBadge: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Kusu baleni')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('Velikost baleni')
    expect(wrapper.text()).toContain('12 x KS')
    expect(wrapper.text()).toContain('Pocet celkem')
    expect(wrapper.text()).toContain('25')
  })
})
