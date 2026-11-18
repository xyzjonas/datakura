/**
 * amount: zisk (profit, order currency)
 * percent: marže - share of the selling price left (selling 100, purchase 70 -> 30 %)
 * markupPercent: přirážka - markup on top of the purchase price (purchase 100, selling 120 -> 20 %)
 */
export type Margin = {
  amount: number
  percent: number
  markupPercent: number
}

export const calculateMargin = (sellingValue: number, purchaseValue: number): Margin => {
  const amount = sellingValue - purchaseValue
  return {
    amount,
    percent: sellingValue > 0 ? (amount / sellingValue) * 100 : 0,
    markupPercent: purchaseValue > 0 ? (amount / purchaseValue) * 100 : 0,
  }
}

type MarginItem = {
  amount: number
  unit_price: number
  total_price?: number
  pricing_details?: { avg_purchase_price: number } | null
  /** Goods taken back from the customer ("vratka"): subtracted from the totals. */
  is_returned?: boolean
}

/** +1 for sold rows, -1 for the returned ones. */
export const itemSign = (item: { is_returned?: boolean }): 1 | -1 => (item.is_returned ? -1 : 1)

export type OrderMarginSummary = Margin & {
  sellingValue: number
  purchaseValue: number
}

/** Order level summary; null when no item carries purchase price info. */
export const calculateOrderMargin = (items?: MarginItem[]): OrderMarginSummary | null => {
  const priced = (items ?? []).filter((item) => item.pricing_details)
  if (!priced.length) {
    return null
  }
  // returned rows are subtracted - neither their value nor their profit counts
  const sellingValue = priced.reduce(
    (sum, item) => sum + itemSign(item) * (item.total_price ?? item.amount * item.unit_price),
    0,
  )
  const purchaseValue = priced.reduce(
    (sum, item) =>
      sum + itemSign(item) * item.amount * (item.pricing_details?.avg_purchase_price ?? 0),
    0,
  )
  return { sellingValue, purchaseValue, ...calculateMargin(sellingValue, purchaseValue) }
}

/** Zisk (profit) in currency units, signed. */
export const formatMargin = (margin: Margin): string => {
  const sign = margin.amount >= 0 ? '+' : ''
  return `${sign}${margin.amount.toFixed(2)}`
}

export const formatMarginPercent = (margin: Margin): string => {
  const sign = margin.percent >= 0 ? '+' : ''
  return `${sign}${margin.percent.toFixed(1)}%`
}

export const formatMarkupPercent = (margin: Margin): string => {
  const sign = margin.markupPercent >= 0 ? '+' : ''
  return `${sign}${margin.markupPercent.toFixed(1)}%`
}
