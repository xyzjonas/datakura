import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { InboundOrderSchema, OutboundOrderSchema } from '@/client'
import InboundOrderGridCard from '../InboundOrderGridCard.vue'
import OutboundOrderGridCard from '../OutboundOrderGridCard.vue'

installQuasarPlugin()

describe('order grid cards', () => {
  it('renders inbound values and routes by code click', async () => {
    const push = vi.fn()
    const order = {
      code: 'IN-001',
      state: 'new',
      supplier: { name: 'ACME Supplier' },
      items: [
        { amount: 2, unit_price: 10 },
        { amount: 1, unit_price: 20 },
      ],
      currency: 'CZK',
    } as unknown as InboundOrderSchema

    const wrapper = mount(InboundOrderGridCard, {
      props: {
        order,
        detailRouteName: 'inboundOrderDetail',
      },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          InboundOrderStateBadge: true,
        },
      },
    })

    expect(wrapper.text()).toContain('IN-001')
    expect(wrapper.text()).toContain('ACME Supplier')
    expect(wrapper.text()).toContain('Počet položek')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('40 CZK')

    await wrapper.find('a.link').trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'inboundOrderDetail',
      params: { code: 'IN-001' },
    })
  })

  it('renders outbound values and routes by code click', async () => {
    const push = vi.fn()
    const order = {
      code: 'OUT-007',
      state: 'new',
      customer: { name: 'Retail Customer' },
      items: [{ amount: 3, unit_price: 12 }],
      currency: 'EUR',
    } as unknown as OutboundOrderSchema

    const wrapper = mount(OutboundOrderGridCard, {
      props: {
        order,
        detailRouteName: 'outboundOrderDetail',
      },
      global: {
        mocks: {
          $router: { push },
        },
        stubs: {
          OutboundOrderStateBadge: true,
        },
      },
    })

    expect(wrapper.text()).toContain('OUT-007')
    expect(wrapper.text()).toContain('Retail Customer')
    expect(wrapper.text()).toContain('Počet položek')
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('36 EUR')

    await wrapper.find('a.link').trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'outboundOrderDetail',
      params: { code: 'OUT-007' },
    })
  })
})
