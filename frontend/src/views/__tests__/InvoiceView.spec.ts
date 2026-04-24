import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import InvoiceView from '@/views/InvoiceView.vue'

const mocks = vi.hoisted(() => ({
  warehouseApiRoutesInvoicesGetInvoice: vi.fn(),
  warehouseApiRoutesInvoicesGetInvoicePdf: vi.fn(),
  clientPut: vi.fn(),
  clientPost: vi.fn(),
  goToInvoice: vi.fn(),
  notify: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesInvoicesGetInvoice: mocks.warehouseApiRoutesInvoicesGetInvoice,
  warehouseApiRoutesInvoicesGetInvoicePdf: mocks.warehouseApiRoutesInvoicesGetInvoicePdf,
}))

vi.mock('@/client/client', () => ({
  formDataBodySerializer: {},
}))

vi.mock('@/client/client.gen', () => ({
  client: {
    put: mocks.clientPut,
    post: mocks.clientPost,
  },
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

vi.mock('@/composables/use-app-router', () => ({
  useAppRouter: () => ({
    goToInvoice: mocks.goToInvoice,
    goToOrderIn: vi.fn(),
    goToOrderOut: vi.fn(),
  }),
}))

vi.mock('quasar', async (importOriginal) => {
  const actual = await importOriginal<typeof import('quasar')>()
  return {
    ...actual,
    useQuasar: () => ({ notify: mocks.notify }),
  }
})

const baseInvoice = {
  created: '2026-04-01T10:00:00Z',
  changed: '2026-04-01T10:00:00Z',
  code: 'INV-001',
  issued_date: '2026-04-01',
  due_date: '2026-04-20',
  payment_method: {
    id: 1,
    name: 'Bank transfer',
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
  },
  external_code: 'EXT-1',
  taxable_supply_date: '2026-04-01',
  paid_date: null,
  currency: 'CZK',
  note: 'Invoice note',
  document: null,
  customer: {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    code: 'CUS-1',
    name: 'Customer',
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
    invoice_due_days: 14,
    block_after_due_days: 30,
    is_self: false,
    data_collection_agreement: false,
    marketing_data_use_agreement: false,
    is_valid: true,
    is_deleted: false,
    owner: null,
    responsible_user: null,
    group: null,
    discount_group: null,
    default_payment_method: null,
    contacts: [],
    note: null,
    register_information: null,
  },
  supplier: {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    code: 'SUP-1',
    name: 'Supplier',
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
    invoice_due_days: 14,
    block_after_due_days: 30,
    is_self: true,
    data_collection_agreement: false,
    marketing_data_use_agreement: false,
    is_valid: true,
    is_deleted: false,
    owner: null,
    responsible_user: null,
    group: null,
    discount_group: null,
    default_payment_method: null,
    contacts: [],
    note: null,
    register_information: null,
  },
  outbound_orders: [
    {
      created: '2026-04-01T10:00:00Z',
      changed: '2026-04-01T10:00:00Z',
      code: 'SORD-1',
      external_code: null,
      state: 'invoiced',
      currency: 'CZK',
      items: [
        {
          created: '2026-04-01T10:00:00Z',
          changed: '2026-04-01T10:00:00Z',
          index: 0,
          amount: 2,
          unit_price: 50,
          total_price: 100,
          product: { code: 'SKU-1', name: 'Product 1', unit: 'ks' },
        },
      ],
    },
  ],
  inbound_orders: [],
}

const ok = (data: unknown) => ({ data: { data } })

describe('InvoiceView', () => {
  beforeEach(() => {
    mocks.warehouseApiRoutesInvoicesGetInvoice.mockReset()
    mocks.warehouseApiRoutesInvoicesGetInvoicePdf.mockReset()
    mocks.clientPut.mockReset()
    mocks.clientPost.mockReset()
    mocks.goToInvoice.mockReset()
    mocks.notify.mockReset()
  })

  it('marks invoice as paid from detail action', async () => {
    mocks.warehouseApiRoutesInvoicesGetInvoice.mockResolvedValue(ok(baseInvoice))
    mocks.clientPost.mockResolvedValue(
      ok({
        ...baseInvoice,
        paid_date: '2026-04-24',
      }),
    )

    const wrapper = mount(InvoiceView, {
      props: { code: 'INV-001' },
      global: {
        stubs: {
          QBtn: {
            props: ['label', 'loading'],
            template:
              '<button :data-label="label" :data-loading="loading" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          },
          QBreadcrumbs: { template: '<div><slot /></div>' },
          QBreadcrumbsEl: { template: '<div><slot /></div>' },
          QMarkupTable: { template: '<table><slot /></table>' },
          PrintDropdownButton: { template: '<div />' },
          ForegroundPanel: { template: '<div><slot /></div>' },
          CustomerCard: { template: '<div><slot /></div>' },
          InboundOrderStateBadge: { template: '<div />' },
          OutboundOrderStateBadge: { template: '<div />' },
          InvoiceUpsertDialog: {
            name: 'InvoiceUpsertDialog',
            props: ['show'],
            template: '<div :data-show="show"></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-label="Označit jako uhrazeno"]').trigger('click')
    await flushPromises()

    expect(mocks.clientPost).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/api/v1/invoices/{invoice_code}/mark-paid',
        path: { invoice_code: 'INV-001' },
      }),
    )
    expect(wrapper.text()).toContain('2026-04-24')
    expect(mocks.notify).toHaveBeenCalled()
  })

  it('saves edited invoice and navigates when code changes', async () => {
    mocks.warehouseApiRoutesInvoicesGetInvoice.mockResolvedValue(ok(baseInvoice))
    mocks.clientPut.mockResolvedValue(
      ok({
        ...baseInvoice,
        code: 'INV-002',
      }),
    )

    const wrapper = mount(InvoiceView, {
      props: { code: 'INV-001' },
      global: {
        stubs: {
          QBtn: {
            props: ['label', 'loading'],
            template:
              '<button :data-label="label" :data-loading="loading" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          },
          QBreadcrumbs: { template: '<div><slot /></div>' },
          QBreadcrumbsEl: { template: '<div><slot /></div>' },
          QMarkupTable: { template: '<table><slot /></table>' },
          PrintDropdownButton: { template: '<div />' },
          ForegroundPanel: { template: '<div><slot /></div>' },
          CustomerCard: { template: '<div><slot /></div>' },
          InboundOrderStateBadge: { template: '<div />' },
          OutboundOrderStateBadge: { template: '<div />' },
          InvoiceUpsertDialog: {
            name: 'InvoiceUpsertDialog',
            props: ['show', 'modelValue'],
            template: '<div :data-show="show"></div>',
          },
        },
      },
    })

    await flushPromises()
    const dialog = wrapper.getComponent({ name: 'InvoiceUpsertDialog' })
    dialog.vm.$emit('submit', {
      body: {
        code: 'INV-002',
        issued_date: '2026-04-01',
        due_date: '2026-04-20',
        payment_method_name: 'Bank transfer',
        taxable_supply_date: '2026-04-01',
        currency: 'CZK',
        customer_code: 'CUS-1',
        supplier_code: 'SUP-1',
        external_code: 'EXT-1',
        paid_date: undefined,
        note: 'Invoice note',
      },
      invoiceFile: null,
    })
    await flushPromises()

    expect(mocks.clientPut).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/api/v1/invoices/{invoice_code}',
        path: { invoice_code: 'INV-001' },
      }),
    )
    expect(mocks.goToInvoice).toHaveBeenCalledWith('INV-002')
    expect(mocks.notify).toHaveBeenCalled()
  })
})
