import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OutboundInvoiceCreateDialog from '../OutboundInvoiceCreateDialog.vue'

installQuasarPlugin()

const customer = {
  created: '2026-04-01T10:00:00Z',
  changed: '2026-04-01T10:00:00Z',
  code: 'CUS-001',
  name: 'Acme',
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
  default_payment_method: {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    id: 1,
    name: 'Bank transfer',
  },
  contacts: [],
  note: null,
  register_information: null,
}

const selfSupplier = {
  ...customer,
  code: 'CUS-SELF',
  name: 'Our Firm',
  is_self: true,
}

const selectedOrders = [
  {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    code: 'SORD-0001',
    external_code: null,
    description: null,
    note: null,
    customer,
    currency: 'CZK',
    state: 'submitted',
    warehouse_order_codes: [],
    requested_delivery_date: null,
    cancelled_date: null,
    fulfilled_date: null,
    items: [],
    warehouse_orders: [
      {
        created: '2026-04-01T10:00:00Z',
        changed: '2026-04-01T10:00:00Z',
        code: 'WOUT-1',
        order_code: 'SORD-0001',
        state: 'completed',
        parent_order: null,
        child_orders: [],
      },
    ],
    credit_note: null,
    invoice: null,
  },
]

describe('OutboundInvoiceCreateDialog', () => {
  it('prefills customer payment method and shows readonly supplier', () => {
    const wrapper = mount(OutboundInvoiceCreateDialog, {
      props: {
        show: true,
        selectedOrders,
        selfSupplier,
      },
      global: {
        stubs: {
          QDialog: { template: '<div><slot /></div>' },
          QCard: { template: '<div><slot /></div>' },
          QForm: { template: '<form><slot /></form>' },
          QBtn: { template: '<button><slot /></button>' },
          QChip: { template: '<div><slot /></div>' },
          QInput: {
            props: ['modelValue', 'label', 'readonly', 'hint'],
            template:
              '<div :data-label="label" :data-model-value="modelValue" :data-readonly="readonly" :data-hint="hint"></div>',
          },
          InvoicePaymentMethodSelect: {
            props: ['modelValue', 'hint', 'placeholder'],
            template:
              '<div data-test="payment-method" :data-model-value="modelValue" :data-hint="hint" :data-placeholder="placeholder"></div>',
          },
        },
      },
    })

    const paymentMethod = wrapper.get('[data-test="payment-method"]')
    expect(paymentMethod.attributes('data-model-value')).toBe('Bank transfer')
    expect(paymentMethod.attributes('data-placeholder')).toBe('Bank transfer')

    const supplierInput = wrapper
      .findAll('[data-label="Dodavatel"]')
      .find((node) => node.attributes('data-model-value') === 'Our Firm')

    expect(supplierInput).toBeTruthy()
    expect(supplierInput?.attributes('data-readonly')).toBe('')
  })
})
