import type {
  InboundOrderSchema,
  InboundWarehouseOrderSchema,
  OutboundOrderSchema,
  OutboundWarehouseOrderSchema,
} from '@/client'

type PagedResponse<TItem> = {
  data?: {
    data: TItem[]
    count: number
  }
  response: {
    ok: boolean
    statusText: string
  }
}

const getErrorMessage = (result: { response: { statusText: string } }, fallback: string) => {
  return result.response.statusText || fallback
}

export const loadAllPagedItems = async <TItem>(
  loadPage: (pageSize: number) => Promise<PagedResponse<TItem>>,
  fallbackErrorMessage: string,
) => {
  const firstResult = await loadPage(1)

  if (!firstResult.response.ok || !firstResult.data) {
    throw new Error(getErrorMessage(firstResult, fallbackErrorMessage))
  }

  if (firstResult.data.count <= firstResult.data.data.length) {
    return firstResult.data.data
  }

  const fullResult = await loadPage(firstResult.data.count)

  if (!fullResult.response.ok || !fullResult.data) {
    throw new Error(getErrorMessage(fullResult, fallbackErrorMessage))
  }

  return fullResult.data.data
}

export const isInboundOrderActive = (order: Pick<InboundOrderSchema, 'state'>) => {
  return !['completed', 'cancelled'].includes(order.state)
}

export const isOutboundOrderActive = (order: Pick<OutboundOrderSchema, 'state'>) => {
  return !['completed', 'completed_paid', 'cancelled'].includes(order.state)
}

export const isInboundWarehouseOrderActive = (
  order: Pick<InboundWarehouseOrderSchema, 'state'>,
) => {
  return !['completed', 'cancelled'].includes(order.state)
}

export const isOutboundWarehouseOrderActive = (
  order: Pick<OutboundWarehouseOrderSchema, 'state'>,
) => {
  return !['completed', 'cancelled'].includes(order.state)
}
