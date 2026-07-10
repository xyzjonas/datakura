import type { InboundOrderItemSchema, OutboundOrderItemSchema } from '@/client'

export function isIndexedOrderItem(
  value: unknown,
): value is (InboundOrderItemSchema | OutboundOrderItemSchema) & { index: number } {
  if (value === null || value === undefined) return false
  if (typeof value !== 'object') return false
  return 'index' in value && typeof (value as Record<string, unknown>).index === 'number'
}
