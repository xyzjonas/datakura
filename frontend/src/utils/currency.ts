/**
 * Documents (orders, calculations) are calculated in the base currency, a customer can be
 * shown / invoiced in another one. `rate` = base currency units per 1 document currency unit,
 * frozen on the document.
 */
export const toBase = (documentAmount: number, rate: number): number => documentAmount * rate

export const fromBase = (baseAmount: number, rate: number): number =>
  rate > 0 ? baseAmount / rate : baseAmount

export const isForeign = (doc?: { currency: string; document_currency?: string | null }) =>
  !!doc?.document_currency && doc.document_currency !== doc.currency
