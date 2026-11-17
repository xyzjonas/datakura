/** How the purchase price of the stock about to be bought differs from the current one. */
export type PurchasePriceDelta = {
  /** newPrice - currentPrice, signed (positive = buying more expensive) */
  amount: number
  /** relative change in %, null when there is no current price to compare with */
  percent: number | null
}

export const calculatePurchasePriceDelta = (
  currentPrice: number,
  newPrice: number,
): PurchasePriceDelta => ({
  amount: newPrice - currentPrice,
  percent: currentPrice > 0 ? ((newPrice - currentPrice) / currentPrice) * 100 : null,
})

const signed = (value: number, digits: number) => `${value > 0 ? '+' : ''}${value.toFixed(digits)}`

export const formatDeltaAmount = (delta: PurchasePriceDelta): string => signed(delta.amount, 2)

export const formatDeltaPercent = (delta: PurchasePriceDelta): string =>
  delta.percent === null ? '' : `${signed(delta.percent, 1)} %`
