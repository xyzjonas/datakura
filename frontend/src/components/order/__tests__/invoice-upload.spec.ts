import { describe, expect, it } from 'vitest'
import type { InvoiceStoreSchema } from '@/client'
import { toInvoiceMultipartBody } from '../invoice-upload'

describe('toInvoiceMultipartBody', () => {
  const baseBody: InvoiceStoreSchema = {
    code: 'INV-2026-001',
    issued_date: '2026-04-01',
    due_date: '2026-04-15',
    payment_method_name: 'Bank transfer',
    taxable_supply_date: '2026-04-01',
    currency: 'CZK',
    customer_code: undefined,
    supplier_code: 'SUP-001',
    external_code: undefined,
    paid_date: undefined,
    note: undefined,
  }

  it('includes invoice_file when a PDF file is provided', () => {
    const pdf = new File(['%PDF-1.4'], 'invoice.pdf', { type: 'application/pdf' })

    const result = toInvoiceMultipartBody({
      body: baseBody,
      invoiceFile: pdf,
    })

    expect(result.invoice_file).toBe(pdf)
    expect(result.code).toBe(baseBody.code)
  })

  it('omits invoice_file when no file is provided', () => {
    const result = toInvoiceMultipartBody({
      body: baseBody,
      invoiceFile: null,
    })

    expect(result.invoice_file).toBeUndefined()
    expect(result.supplier_code).toBe(baseBody.supplier_code)
  })
})
