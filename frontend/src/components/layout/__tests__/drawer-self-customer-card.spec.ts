import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DrawerSelfCustomerCard from '../DrawerSelfCustomerCard.vue'

const { getCustomersMock } = vi.hoisted(() => ({
  getCustomersMock: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesCustomerGetCustomers: getCustomersMock,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown; response: Response }) =>
      response.response.ok ? response.data : undefined,
  }),
}))

installQuasarPlugin()

const buildResponse = (data: unknown) => ({
  data,
  error: undefined,
  request: new Request('http://localhost/api/v1/customers'),
  response: new Response(null, { status: 200 }),
})

const selfCustomer = {
  created: '2026-04-01T10:00:00Z',
  changed: '2026-04-01T10:00:00Z',
  code: 'SELF-001',
  name: 'Datakura s.r.o.',
  email: '',
  phone: '',
  street: '',
  city: '',
  postal_code: '',
  state: 'CZ',
  tax_identification: '',
  identification: '',
  customer_type: 'FIRMA',
  price_type: 'FIRMY',
  invoice_due_days: 21,
  block_after_due_days: 30,
  is_self: true,
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
  default_payment_method: null,
  contacts: [],
  note: null,
  register_information: null,
}

describe('DrawerSelfCustomerCard', () => {
  beforeEach(() => {
    getCustomersMock.mockReset()
  })

  it('shows self customer name from paginated customers endpoint', async () => {
    getCustomersMock.mockResolvedValue(
      buildResponse({
        count: 1,
        next: null,
        previous: null,
        data: [selfCustomer],
      }),
    )

    const wrapper = mount(DrawerSelfCustomerCard, {
      global: {
        stubs: {
          QCard: { template: '<div><slot /></div>' },
          QCardSection: { template: '<div><slot /></div>' },
          QIcon: { template: '<i />' },
          QSkeleton: { template: '<div data-test="skeleton" />' },
        },
      },
    })

    await flushPromises()

    expect(getCustomersMock).toHaveBeenCalledWith(
      expect.objectContaining({
        query: expect.objectContaining({
          is_self: true,
          page: 1,
          page_size: 1,
        }),
      }),
    )
    expect(wrapper.text()).toContain('Datakura s.r.o.')
    expect(wrapper.text()).not.toContain('Vlastní firma zatím není nastavená.')
  })

  it('shows Czech help message when self customer missing', async () => {
    getCustomersMock.mockResolvedValue(
      buildResponse({
        count: 0,
        next: null,
        previous: null,
        data: [],
      }),
    )

    const wrapper = mount(DrawerSelfCustomerCard, {
      global: {
        stubs: {
          QCard: { template: '<div><slot /></div>' },
          QCardSection: { template: '<div><slot /></div>' },
          QIcon: { template: '<i />' },
          QSkeleton: { template: '<div data-test="skeleton" />' },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Nenastaveno')
  })
})
