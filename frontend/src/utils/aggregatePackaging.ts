import type { WarehouseItemSchema } from '@/client'
import { round } from './round'

export interface WarehouseItemSchemaWithCount extends WarehouseItemSchema {
  itemsCount: number
}

export const aggregatePackaging = (locationItems: WarehouseItemSchema[]) => {
  return Object.values(
    locationItems.reduce(
      (acc, item) => {
        const key = `${item.product.code}_${item.unit_of_measure}_${item.package?.type ?? '---'}`

        if (!acc[key]) {
          acc[key] = {
            ...item,
            itemsCount: 1,
          }
        } else {
          acc[key].itemsCount += 1
          acc[key].amount = round(acc[key].amount + item.amount)
        }

        return acc
      },
      {} as Record<string, WarehouseItemSchemaWithCount>,
    ),
  )
}
