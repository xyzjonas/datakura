import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import CustomerInboundOrdersWidget from '@/components/customer/CustomerInboundOrdersWidget.vue'
import CustomerOutboundOrdersWidget from '@/components/customer/CustomerOutboundOrdersWidget.vue'
import OutboundCalculationCreateButton from '../OutboundCalculationCreateButton.vue'
import OutboundOrdersTable from '../OutboundOrdersTable.vue'
import SimpleInboundOrdersTable from '../SimpleInboundOrdersTable.vue'
import SimpleOutboundOrdersTable from '../SimpleOutboundOrdersTable.vue'

const mocks = vi.hoisted(() => ({
  getOutboundOrders: vi.fn(),
  getInboundOrders: vi.fn(),
  goToOrderOut: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesOutboundOrdersGetOutboundOrders: mocks.getOutboundOrders,
  warehouseApiRoutesOutboundOrdersCreateOutboundOrder: vi.fn(),
  warehouseApiRoutesInboundOrdersGetInboundOrders: mocks.getInboundOrders,
}))

vi.mock('@/composables/query/use-products-query', async () => {
  const { ref } = await import('vue')
  return {
    useQueryProducts: () => ({
      page: ref(1),
      pageSize: ref(20),
      search: ref(''),
      stockProductCode: ref<string | null>(null),
      includeAll: ref(false),
    }),
  }
})

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (result: { data?: unknown }) => result.data,
  }),
}))

vi.mock('@/composables/use-app-router', () => ({
  useAppRouter: () => ({ goToOrderOut: mocks.goToOrderOut }),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ currentRoute: ref({}), push: vi.fn() }) }
})

installQuasarPlugin()

const stubs = {
  SearchInput: true,
  CustomerSearchSelect: true,
  StockProductSearchSelect: true,
  CustomerLink: true,
  OutboundOrderGridCard: true,
  InboundOrderGridCard: true,
  OutboundOrderStateBadge: true,
  InboundOrderStateBadge: true,
  OutboundWarehouseOrderStateBadge: true,
}

const outboundOrder = {
  code: 'OV2026100001',
  calculation_code: 'K2026100007',
  state: 'picking',
  is_calculation: false,
  created: '2026-10-01T10:00:00Z',
  customer: { code: 'CUS', name: 'Acme' },
  currency: 'CZK',
  items: [],
  warehouse_orders: [],
  warehouse_order_codes: [],
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.getOutboundOrders.mockResolvedValue({ data: { data: [outboundOrder], count: 1 } })
  mocks.getInboundOrders.mockResolvedValue({ data: { data: [], count: 0 } })
})

describe('OutboundOrdersTable calculations', () => {
  it('requests orders (no calculations flag) and shows the preserved calculation number', async () => {
    const wrapper = mount(OutboundOrdersTable, { global: { stubs } })
    await flushPromises()

    expect(mocks.getOutboundOrders.mock.calls[0]![0].query.calculations).toBeUndefined()
    expect(wrapper.text()).toContain('Kalkulace')
    expect(wrapper.text()).toContain('K2026100007')
    expect(wrapper.text()).toContain('Vydejka')
  })

  it('requests calculations and hides calculation + warehouse columns', async () => {
    const wrapper = mount(OutboundOrdersTable, {
      props: { calculations: true },
      global: { stubs },
    })
    await flushPromises()

    expect(mocks.getOutboundOrders.mock.calls[0]![0].query.calculations).toBe(true)
    expect(wrapper.text()).not.toContain('Kalkulace')
    expect(wrapper.text()).not.toContain('Vydejka')
  })
})

describe('Simple tables', () => {
  it('outbound: passes customer, calculations and include_all', async () => {
    mount(SimpleOutboundOrdersTable, {
      props: { customerCode: 'CUS-1', calculations: true, includeAll: true },
      global: { stubs },
    })
    await flushPromises()

    expect(mocks.getOutboundOrders).toHaveBeenCalledWith({
      query: expect.objectContaining({
        customer_code: 'CUS-1',
        calculations: true,
        include_all: true,
        page: 1,
        page_size: 5,
      }),
    })
  })

  it('outbound: omits optional flags and refetches when the customer changes', async () => {
    const wrapper = mount(SimpleOutboundOrdersTable, {
      props: { stockProductCode: 'PRD-1' },
      global: { stubs },
    })
    await flushPromises()

    const query = mocks.getOutboundOrders.mock.calls[0]![0].query
    expect(query.calculations).toBeUndefined()
    expect(query.include_all).toBeUndefined()
    expect(query.customer_code).toBeUndefined()

    await wrapper.setProps({ customerCode: 'CUS-2' })
    await flushPromises()

    expect(mocks.getOutboundOrders).toHaveBeenCalledTimes(2)
    expect(mocks.getOutboundOrders.mock.calls[1]![0].query.customer_code).toBe('CUS-2')
  })

  it('inbound: passes supplier and include_all, never calculations', async () => {
    mount(SimpleInboundOrdersTable, {
      props: { supplierCode: 'SUP-1', includeAll: true },
      global: { stubs },
    })
    await flushPromises()

    const query = mocks.getInboundOrders.mock.calls[0]![0].query
    expect(query).toMatchObject({ supplier_code: 'SUP-1', include_all: true })
    expect(query).not.toHaveProperty('calculations')
  })
})

describe('Customer widgets', () => {
  it('buyer: lists all-state sales orders', async () => {
    const wrapper = mount(CustomerOutboundOrdersWidget, {
      props: { customerCode: 'CUS-1' },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Historie objednávek')
    const query = mocks.getOutboundOrders.mock.calls[0]![0].query
    expect(query).toMatchObject({ customer_code: 'CUS-1', include_all: true })
    expect(query.calculations).toBeUndefined()
  })

  it('buyer: lists all-state calculations', async () => {
    const wrapper = mount(CustomerOutboundOrdersWidget, {
      props: { customerCode: 'CUS-1', calculations: true },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Kalkulace')
    expect(mocks.getOutboundOrders.mock.calls[0]![0].query).toMatchObject({
      customer_code: 'CUS-1',
      include_all: true,
      calculations: true,
    })
  })

  it('supplier: lists all-state purchase orders and never touches sales orders', async () => {
    const wrapper = mount(CustomerInboundOrdersWidget, {
      props: { customerCode: 'SUP-1' },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Historie vydaných objednávek')
    expect(mocks.getInboundOrders.mock.calls[0]![0].query).toMatchObject({
      supplier_code: 'SUP-1',
      include_all: true,
    })
    expect(mocks.getOutboundOrders).not.toHaveBeenCalled()
  })
})

describe('OutboundCalculationCreateButton', () => {
  it('is labelled "nová kalkulace"', () => {
    const wrapper = mount(OutboundCalculationCreateButton, {
      global: { stubs: { NewOrderDialog: true } },
    })

    expect(wrapper.text()).toContain('nová kalkulace')
  })
})
