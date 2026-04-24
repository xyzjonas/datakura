import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import InvoiceUpsertDialog from '../InvoiceUpsertDialog.vue'

installQuasarPlugin()

const customer = {
  created: '2026-04-01T10:00:00Z',
  changed: '2026-04-01T10:00:00Z',
  code: 'CUS-SELF',
  name: 'Self Company',
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

const supplier = {
  ...customer,
  code: 'SUP-001',
  name: 'Supplier Co',
  is_self: false,
}

describe('InvoiceUpsertDialog', () => {
  it('shows both fields without party switch and submits locked customer code', async () => {
    const wrapper = mount(InvoiceUpsertDialog, {
      props: {
        show: true,
        modelValue: {
          code: 'INV-001',
          currency: 'CZK',
          issued_date: '2026-04-01',
          due_date: '2026-04-15',
          taxable_supply_date: '2026-04-01',
          payment_method_name: '',
          customer_code: undefined,
          supplier_code: undefined,
          external_code: undefined,
          paid_date: undefined,
          note: undefined,
        },
        defaultCustomer: customer,
        defaultSupplier: supplier,
        lockCustomer: true,
      },
      global: {
        stubs: {
          QDialog: {
            template: '<div><slot /></div>',
          },
          QCard: {
            template: '<div><slot /></div>',
          },
          QForm: {
            template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>',
          },
          QInput: {
            template: '<input />',
          },
          QFile: {
            template: '<input type="file" />',
          },
          QSelect: {
            props: ['options'],
            template: '<select />',
          },
          QBtn: {
            template: '<button><slot /></button>',
          },
          CustomerSearchSelect: {
            props: ['label', 'disable'],
            template: '<div :data-disable="disable">{{ label }}</div>',
          },
          InvoicePaymentMethodSelect: {
            template: '<div>Platební metoda</div>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Odběratel')
    expect(wrapper.text()).toContain('Dodavatel')
    expect(wrapper.text()).not.toContain('Typ protistrany pro fakturu')

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')?.at(-1)).toEqual([
      {
        body: {
          code: 'INV-001',
          currency: 'CZK',
          issued_date: '2026-04-01',
          due_date: '2026-04-15',
          taxable_supply_date: '2026-04-01',
          payment_method_name: 'Bank transfer',
          customer_code: 'CUS-SELF',
          supplier_code: 'SUP-001',
          external_code: undefined,
          paid_date: undefined,
          note: undefined,
        },
        invoiceFile: null,
      },
    ])
  })
})
