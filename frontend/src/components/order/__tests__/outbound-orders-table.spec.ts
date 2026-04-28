import type { CustomerSchema } from '@/client'
import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import OutboundOrdersTable from '../OutboundOrdersTable.vue'

const mocks = vi.hoisted(() => ({
  getOutboundOrders: vi.fn(),
  routerPush: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesOutboundOrdersGetOutboundOrders: mocks.getOutboundOrders,
}))

vi.mock('@/composables/query/use-products-query', async () => {
  const { ref } = await import('vue')
  return {
    useQueryProducts: () => ({
      page: ref(1),
      pageSize: ref(20),
      search: ref(''),
      stockProductCode: ref<string | null>(null),
    }),
  }
})

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ push: mocks.routerPush }),
  }
})

installQuasarPlugin()

type CustomerFilterFixture = Pick<
  CustomerSchema,
  'code' | 'name' | 'invoice_due_days' | 'default_payment_method'
>

const createCustomer = (fixture: CustomerFilterFixture): CustomerSchema => ({
  created: '2026-04-01T10:00:00Z',
  changed: '2026-04-01T10:00:00Z',
  name: fixture.name,
  email: null,
  phone: null,
  code: fixture.code,
  street: null,
  city: null,
  postal_code: null,
  state: 'CZ',
  tax_identification: null,
  identification: null,
  customer_type: 'FIRMA',
  price_type: 'FIRMY',
  invoice_due_days: fixture.invoice_due_days,
  block_after_due_days: 30,
  is_self: false,
  data_collection_agreement: false,
  marketing_data_use_agreement: false,
  is_valid: true,
  is_deleted: false,
  owner: null,
  responsible_user: null,
  group: {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    code: 'GRP-001',
    name: 'Default',
  },
  discount_group: null,
  default_payment_method: fixture.default_payment_method,
  contacts: [],
  note: null,
  register_information: null,
})

const customer = createCustomer({
  code: 'CUS-001',
  name: 'Acme',
  invoice_due_days: 14,
  default_payment_method: null,
})

const order = {
  code: 'SORD-001',
  state: 'sent',
  created: '2026-04-01T10:00:00Z',
  external_code: null,
  customer,
  currency: 'CZK',
  items: [{ amount: 2, unit_price: 50 }],
  warehouse_orders: [{ code: 'WOUT-001', state: 'completed' }],
  warehouse_order_codes: ['WOUT-001'],
  invoice: null,
}

describe('OutboundOrdersTable', () => {
  beforeEach(() => {
    mocks.getOutboundOrders.mockReset()
    mocks.routerPush.mockReset()
    mocks.getOutboundOrders.mockResolvedValue({
      data: {
        data: [order],
        count: 1,
      },
    })
  })

  it('sends customer_code query when customer filter exists', async () => {
    mount(OutboundOrdersTable, {
      props: {
        customerFilter: customer,
      },
      global: {
        stubs: {
          SearchInput: true,
          CustomerSearchSelect: true,
          StockProductSearchSelect: true,
          OutboundOrderGridCard: true,
          OutboundOrderStateBadge: true,
          OutboundWarehouseOrderStateBadge: true,
          CustomerLink: {
            template: '<span>{{ customer.name }}</span>',
            props: ['customer'],
          },
          QTooltip: {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    await flushPromises()

    expect(mocks.getOutboundOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        query: expect.objectContaining({
          customer_code: 'CUS-001',
        }),
      }),
    )
  })

  it('emits customer when filter icon next to customer cell clicked', async () => {
    const wrapper = mount(OutboundOrdersTable, {
      global: {
        stubs: {
          SearchInput: true,
          CustomerSearchSelect: true,
          StockProductSearchSelect: true,
          OutboundOrderGridCard: true,
          OutboundOrderStateBadge: true,
          OutboundWarehouseOrderStateBadge: true,
          CustomerLink: {
            template: '<span>{{ customer.name }}</span>',
            props: ['customer'],
          },
          QBtn: {
            template: '<button v-bind="$attrs" @click="$emit(\'click\', $event)"><slot /></button>',
          },
          QTooltip: {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[aria-label="Filtrovat odberatele"]').trigger('click')

    expect(wrapper.emitted('applyCustomerFilter')?.at(-1)).toEqual([customer])
  })
})