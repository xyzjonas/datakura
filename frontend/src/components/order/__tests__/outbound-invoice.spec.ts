import type { OutboundOrderSchema } from '@/client'
import {
  canGroupOutboundOrderForInvoice,
  createDefaultOutboundInvoiceForm,
  getOutboundInvoiceSelectionBlockReason,
} from '@/components/order/outbound-invoice'
import { describe, expect, it, vi } from 'vitest'

const buildOrder = (overrides: Partial<OutboundOrderSchema> = {}): OutboundOrderSchema => {
  const code = overrides.code ?? 'SORD-0001'

  return {
    created: '2026-04-01T10:00:00Z',
    changed: '2026-04-01T10:00:00Z',
    code,
    external_code: null,
    description: null,
    note: null,
    currency: 'CZK',
    customer: {
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
    },
    items: [],
    state: 'submitted',
    warehouse_orders: [
      {
        created: '2026-04-01T10:00:00Z',
        changed: '2026-04-01T10:00:00Z',
        code: `WOUT-${code}`,
        order_code: code,
        state: 'completed',
        parent_order: null,
        child_orders: [],
      },
    ],
    credit_note: null,
    invoice: null,
    requested_delivery_date: null,
    cancelled_date: null,
    fulfilled_date: null,
    warehouse_order_codes: [],
    ...overrides,
  }
}

describe('outbound invoice helpers', () => {
  it('creates default form from selected orders and customer due days', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-10T08:30:00Z'))

    const form = createDefaultOutboundInvoiceForm([buildOrder(), buildOrder({ code: 'SORD-0002' })])

    expect(form.order_codes).toEqual(['SORD-0001', 'SORD-0002'])
    expect(form.issued_date).toBe('2026-04-10')
    expect(form.taxable_supply_date).toBe('2026-04-10')
    expect(form.due_date).toBe('2026-05-01')
    expect(form.payment_method_name).toBe('Bank transfer')

    vi.useRealTimers()
  })

  it('blocks selection for incompatible outbound orders', () => {
    const anchorOrder = buildOrder()

    expect(
      getOutboundInvoiceSelectionBlockReason(buildOrder({ invoice: { code: 'INV-1' } as never })),
    ).toBe('already-invoiced')
    expect(getOutboundInvoiceSelectionBlockReason(buildOrder({ state: 'draft' }))).toBe('draft')
    expect(getOutboundInvoiceSelectionBlockReason(buildOrder({ warehouse_orders: [] }))).toBe(
      'warehouse-not-completed',
    )
    expect(
      getOutboundInvoiceSelectionBlockReason(
        buildOrder({ customer: { ...anchorOrder.customer, code: 'CUS-002' } }),
        anchorOrder,
      ),
    ).toBe('different-customer')
    expect(
      getOutboundInvoiceSelectionBlockReason(buildOrder({ currency: 'EUR' }), anchorOrder),
    ).toBe('different-currency')
    expect(
      canGroupOutboundOrderForInvoice(
        buildOrder({
          code: 'SORD-0002',
          warehouse_orders: [
            {
              created: '2026-04-01T10:00:00Z',
              changed: '2026-04-01T10:00:00Z',
              code: 'WOUT-1',
              order_code: 'SORD-0002',
              state: 'completed',
              parent_order: null,
              child_orders: [],
            },
          ],
        }),
        anchorOrder,
      ),
    ).toBe(true)
  })
})
