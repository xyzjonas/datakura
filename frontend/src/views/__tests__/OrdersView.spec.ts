import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import OrdersView from '@/views/OrdersView.vue'

vi.mock('@/components/LargeTabs.vue', () => ({
  default: {
    name: 'LargeTabs',
    props: {
      tab: {
        type: String,
        required: true,
      },
      items: {
        type: Array,
        required: false,
        default: () => [],
      },
    },
    emits: ['update:tab'],
    template: `
      <div>
        <button data-test="tab-inbound" @click="$emit('update:tab', 'inbound')">inbound</button>
        <button data-test="tab-outbound" @click="$emit('update:tab', 'outbound')">outbound</button>
      </div>
    `,
  },
}))

vi.mock('@/components/order/InboundOrdersView.vue', () => ({
  default: {
    name: 'InboundOrdersView',
    template: '<div data-test="inbound-view">Inbound</div>',
  },
}))

vi.mock('@/components/order/OutboundOrdersView.vue', () => ({
  default: {
    name: 'OutboundOrdersView',
    template: '<div data-test="outbound-view">Outbound</div>',
  },
}))

const createTestRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/orders',
        component: OrdersView,
      },
    ],
  })

describe('OrdersView', () => {
  it('uses inbound as default and normalizes query', async () => {
    const router = createTestRouter()
    router.push('/orders')
    await router.isReady()

    const wrapper = mount(OrdersView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(router.currentRoute.value.query.tab).toBe('inbound')
    expect(wrapper.find('[data-test="inbound-view"]').exists()).toBe(true)
  })

  it('uses outbound when tab query is valid', async () => {
    const router = createTestRouter()
    router.push('/orders?tab=outbound')
    await router.isReady()

    const wrapper = mount(OrdersView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(router.currentRoute.value.query.tab).toBe('outbound')
    expect(wrapper.find('[data-test="outbound-view"]').exists()).toBe(true)
  })

  it('falls back to inbound when tab query is invalid', async () => {
    const router = createTestRouter()
    router.push('/orders?tab=invalid')
    await router.isReady()

    const wrapper = mount(OrdersView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(router.currentRoute.value.query.tab).toBe('inbound')
    expect(wrapper.find('[data-test="inbound-view"]').exists()).toBe(true)
  })

  it('updates query when user switches tabs', async () => {
    const router = createTestRouter()
    router.push('/orders?tab=inbound')
    await router.isReady()

    const wrapper = mount(OrdersView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()
    await wrapper.find('[data-test="tab-outbound"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.tab).toBe('outbound')
    expect(wrapper.find('[data-test="outbound-view"]').exists()).toBe(true)
  })
})
