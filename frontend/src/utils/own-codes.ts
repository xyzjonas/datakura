/** Items of an order of a customer ordering by own codes, that still lack the code. */
export const itemsMissingOwnCode = <T extends { customer_product_code?: string | null }>(order: {
  customer: { requires_own_codes?: boolean }
  items?: T[]
}): T[] => {
  if (!order.customer.requires_own_codes) {
    return []
  }
  return (order.items ?? []).filter((item) => !item.customer_product_code)
}
