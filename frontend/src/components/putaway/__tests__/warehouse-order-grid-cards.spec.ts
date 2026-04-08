import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { InboundWarehouseOrderSchema, OutboundWarehouseOrderSchema } from '@/client'
import InboundWarehouseOrderGridCard from '../InboundWarehouseOrderGridCard.vue'
import OutboundWarehouseOrderGridCard from '../OutboundWarehouseOrderGridCard.vue'

installQuasarPlugin()

describe('warehouse order grid cards', () => {
  it('renders inbound warehouse card and routes via both links', async () => {
    const push = vi.fn()
    const order = {
      code: 'WIN-001',
      state: 'created',
      order: {
        code: 'IN-001',
        supplier: { name: 'Supplier A' },
      },
      remaining_amount: 25,
      total_amount: 100,
    } as unknown as InboundWarehouseOrderSchema

    const wrapper = mount(InboundWarehouseOrderGridCard, {
      props: { order },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          InboundWarehouseOrderStateBadge: true,
          OrderProgress: true,
        },
      },
    })

    expect(wrapper.text()).toContain('WIN-001')
    expect(wrapper.text()).toContain('IN-001')
    expect(wrapper.text()).toContain('Supplier A')

    const links = wrapper.findAll('a.link')
    await links[0].trigger('click')
    await links[1].trigger('click')

    expect(push).toHaveBeenNthCalledWith(1, {
      name: 'warehouseInboundOrderDetail',
      params: { code: 'WIN-001' },
    })
    expect(push).toHaveBeenNthCalledWith(2, {
      name: 'inboundOrderDetail',
      params: { code: 'IN-001' },
    })
  })

  it('renders outbound warehouse card and routes via both links', async () => {
    const push = vi.fn()
    const order = {
      code: 'WOUT-002',
      state: 'created',
      order: {
        code: 'OUT-002',
        customer: { name: 'Customer B' },
      },
      remaining_amount: 50,
      total_amount: 120,
    } as unknown as OutboundWarehouseOrderSchema

    const wrapper = mount(OutboundWarehouseOrderGridCard, {
      props: { order },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          OutboundWarehouseOrderStateBadge: true,
          OrderProgress: true,
        },
      },
    })

    expect(wrapper.text()).toContain('WOUT-002')
    expect(wrapper.text()).toContain('OUT-002')
    expect(wrapper.text()).toContain('Customer B')

    const links = wrapper.findAll('a.link')
    await links[0].trigger('click')
    await links[1].trigger('click')

    expect(push).toHaveBeenNthCalledWith(1, {
      name: 'warehouseOutboundOrderDetail',
      params: { code: 'WOUT-002' },
    })
    expect(push).toHaveBeenNthCalledWith(2, {
      name: 'outboundOrderDetail',
      params: { code: 'OUT-002' },
    })
  })
})
