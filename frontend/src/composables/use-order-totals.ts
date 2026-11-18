import { formatNumber } from '@/utils/format-number'
import { useMinimumProfit } from '@/composables/use-minimum-profit'
import { calculateOrderMargin, itemSign } from '@/utils/margin'
import { isBelowMinimumProfit } from '@/utils/minimum-profit'
import { round } from '@/utils/round'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

export type OrderTotalsSource = {
  currency: string
  items?: {
    amount: number
    unit_price: number
    total_price?: number
    pricing_details?: { avg_purchase_price: number } | null
    product?: { unit_weight?: number | null }
    /** Goods taken back from the customer: subtracted from the totals. */
    is_returned?: boolean
  }[]
}

export const useOrderTotals = (order: MaybeRefOrGetter<OrderTotalsSource | null | undefined>) => {
  const currency = computed(() => toValue(order)?.currency ?? '')
  const totalPrice = computed(() =>
    (toValue(order)?.items ?? []).reduce(
      (sum, item) => sum + itemSign(item) * (item.total_price ?? item.amount * item.unit_price),
      0,
    ),
  )
  const isMarginPositive = computed(() =>
    orderMargin.value ? orderMargin.value.amount > 0 : false,
  )
  const { minimumMarkupPercent } = useMinimumProfit()
  const isBelowMinimum = computed(() =>
    orderMargin.value
      ? isBelowMinimumProfit(
          orderMargin.value.sellingValue,
          orderMargin.value.purchaseValue,
          minimumMarkupPercent.value,
        )
      : false,
  )
  const formattedTotalPrice = computed(() => formatNumber(totalPrice.value))
  const orderMargin = computed(() => calculateOrderMargin(toValue(order)?.items))
  const formattedPurchaseValue = computed(() =>
    orderMargin.value ? formatNumber(round(orderMargin.value.purchaseValue)) : '0',
  )
  const formattedMarginValue = computed(() =>
    orderMargin.value
      ? `${isMarginPositive.value ? '+' : ''}${formatNumber(round(orderMargin.value.amount))}`
      : '0',
  )

  const formattedMarginPercent = computed(() =>
    orderMargin.value
      ? `${isMarginPositive.value ? '+' : ''}${formatNumber(round(orderMargin.value.percent))}%`
      : '',
  )

  const formattedMarkupPercent = computed(() =>
    orderMargin.value
      ? `${isMarginPositive.value ? '+' : ''}${formatNumber(round(orderMargin.value.markupPercent))}%`
      : '',
  )

  const totalWeight = computed(() => {
    return (toValue(order)?.items ?? []).reduce(
      (sum, item) => sum + itemSign(item) * item.amount * (item.product?.unit_weight ?? 0),
      0,
    )
  })
  const formattedWeight = computed(() => {
    // Avoid binary float rounding errors (e.g. 3 * 0.575 = 1.7249... → "1.72" instead of "1.73")
    return (Math.round((totalWeight.value + Number.EPSILON) * 100) / 100).toFixed(2)
  })

  return {
    currency,
    totalPrice,
    formattedTotalPrice,
    orderMargin,
    formattedPurchaseValue,
    formattedMarginValue,
    formattedMarginPercent,
    formattedMarkupPercent,
    totalWeight,
    formattedWeight,
    isMarginPositive,
    isBelowMinimum,
  }
}
