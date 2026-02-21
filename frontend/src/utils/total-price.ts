import { round } from './round'

export const calculateTotalPrice = (items?: { amount: number; unit_price: number }[]) => {
  return round((items ?? []).reduce((sum, item) => sum + item.amount * item.unit_price, 0))
}
