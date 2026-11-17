/**
 * The minimum allowed profit is stored as přirážka (markup on top of the purchase price, in %).
 * Marže (share of the selling price) is just another way of expressing the very same number:
 *   marže = markup / (100 + markup), markup = marže / (100 - marže)
 */
export type ProfitBasis = 'markup' | 'margin'

/** Markup (%) -> margin (%). */
export const markupToMargin = (markup: number): number => (markup / (100 + markup)) * 100

/** Margin (%) -> markup (%); margin has to be < 100 %. */
export const marginToMarkup = (margin: number): number => (margin / (100 - margin)) * 100

// totals are displayed with 2 decimals, don't flag what only differs by float noise
const TOLERANCE = 0.005

/**
 * Selling `sellingValue` of goods bought for `purchaseValue` earns less than the minimum markup.
 * No guard (0 / unset) or no purchase price known = never below.
 */
export const isBelowMinimumProfit = (
  sellingValue: number,
  purchaseValue: number,
  minimumMarkupPercent: number | null | undefined,
): boolean => {
  if (!minimumMarkupPercent || minimumMarkupPercent <= 0 || purchaseValue <= 0) {
    return false
  }
  return sellingValue < purchaseValue * (1 + minimumMarkupPercent / 100) - TOLERANCE
}

type GuardedItem = {
  amount: number
  unit_price: number
  total_price?: number
  pricing_details?: { avg_purchase_price?: number } | null
  product?: { purchase_price?: number | null }
}

export const itemIsBelowMinimumProfit = (
  item: GuardedItem,
  minimumMarkupPercent: number | null | undefined,
): boolean => {
  const purchasePrice =
    item.pricing_details?.avg_purchase_price ?? item.product?.purchase_price ?? 0
  return isBelowMinimumProfit(
    Number(item.total_price ?? item.amount * item.unit_price),
    item.amount * purchasePrice,
    minimumMarkupPercent,
  )
}

export const itemsBelowMinimumProfit = <T extends GuardedItem>(
  items: T[] | undefined,
  minimumMarkupPercent: number | null | undefined,
): T[] => (items ?? []).filter((item) => itemIsBelowMinimumProfit(item, minimumMarkupPercent))
