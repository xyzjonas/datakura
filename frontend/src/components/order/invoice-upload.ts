import type { InvoiceStoreSchema } from '@/client'

export type InvoiceUpsertSubmitPayload = {
  body: InvoiceStoreSchema
  invoiceFile: File | null
}

export type InvoiceMultipartBody = InvoiceStoreSchema & {
  invoice_file?: File
}

export const toInvoiceMultipartBody = (
  payload: InvoiceUpsertSubmitPayload,
): InvoiceMultipartBody => ({
  ...payload.body,
  invoice_file: payload.invoiceFile ?? undefined,
})
