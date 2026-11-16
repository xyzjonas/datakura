import {
  warehouseApiRoutesOutboundCalculationsAddItemToOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsCreateOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsDuplicateOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsGetOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsGetOutboundCalculations,
  warehouseApiRoutesOutboundCalculationsRemoveItemFromOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsReorderItemInOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsSetOutboundCalculationOriginCountry,
  warehouseApiRoutesOutboundCalculationsUpdateItemInOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsUpdateOutboundCalculation,
  warehouseApiRoutesOutboundOrdersAddItemToOutboundOrder,
  warehouseApiRoutesOutboundOrdersCreateOutboundOrder,
  warehouseApiRoutesOutboundOrdersDuplicateOutboundOrder,
  warehouseApiRoutesOutboundOrdersGetOutboundOrder,
  warehouseApiRoutesOutboundOrdersGetOutboundOrders,
  warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder,
  warehouseApiRoutesOutboundOrdersReorderItemInOutboundOrder,
  warehouseApiRoutesOutboundOrdersSetOutboundOrderOriginCountry,
  warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder,
  warehouseApiRoutesOutboundOrdersUpdateOutboundOrder,
  type OutboundCalculationCreateOrUpdateSchema,
  type OutboundCalculationSchema,
  type OutboundOrderItemCreateSchema,
  type OutboundOrderSchema,
} from '@/client'
import { computed, inject, provide, toValue, type InjectionKey, type MaybeRefOrGetter } from 'vue'

/**
 * Outbound orders and calculations are two separate tables with the very same shape
 * and endpoints. This is the single place that knows which SDK function belongs to which,
 * so views/components can be written once for both.
 */
export type OutboundDocumentKind = 'order' | 'calculation'
export type OutboundDocument = OutboundOrderSchema | OutboundCalculationSchema

export type OutboundDocumentListQuery = {
  page?: number
  page_size?: number
  search_term?: string | null
  customer_code?: string | null
  stock_product_code?: string | null
  include_all?: boolean
}

const KIND_KEY: InjectionKey<OutboundDocumentKind> = Symbol('outbound-document-kind')

/** Lets all descendants (item rows, dialogs...) talk to the right API without prop drilling. */
export const provideOutboundDocumentKind = (kind: OutboundDocumentKind) => provide(KIND_KEY, kind)

const REQUIRES_ORIGIN_COUNTRY_KEY: InjectionKey<MaybeRefOrGetter<boolean>> = Symbol(
  'outbound-requires-origin-country',
)

/** The customer of the document needs the origin country on every item. */
export const provideRequiresOriginCountry = (requires: MaybeRefOrGetter<boolean>) =>
  provide(REQUIRES_ORIGIN_COUNTRY_KEY, requires)

export const useRequiresOriginCountry = () => {
  const injected = inject(REQUIRES_ORIGIN_COUNTRY_KEY, false)
  return computed(() => toValue(injected))
}

export const useOutboundDocumentApi = (kind?: MaybeRefOrGetter<OutboundDocumentKind>) => {
  const injectedKind = inject(KIND_KEY, 'order')
  const isCalculation = () => (toValue(kind) ?? injectedKind) === 'calculation'

  const list = (query: OutboundDocumentListQuery) => {
    const cleaned = {
      ...query,
      search_term: query.search_term || undefined,
      customer_code: query.customer_code || undefined,
      stock_product_code: query.stock_product_code || undefined,
      include_all: query.include_all || undefined,
    }
    return isCalculation()
      ? warehouseApiRoutesOutboundCalculationsGetOutboundCalculations({ query: cleaned })
      : warehouseApiRoutesOutboundOrdersGetOutboundOrders({ query: cleaned })
  }

  const get = (code: string) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsGetOutboundCalculation({
          path: { calculation_code: code },
        })
      : warehouseApiRoutesOutboundOrdersGetOutboundOrder({ path: { order_code: code } })

  const create = (body: OutboundCalculationCreateOrUpdateSchema) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsCreateOutboundCalculation({ body })
      : warehouseApiRoutesOutboundOrdersCreateOutboundOrder({ body })

  const update = (code: string, body: OutboundCalculationCreateOrUpdateSchema) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsUpdateOutboundCalculation({
          path: { calculation_code: code },
          body,
        })
      : warehouseApiRoutesOutboundOrdersUpdateOutboundOrder({
          path: { order_code: code },
          body,
        })

  const duplicate = (code: string) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsDuplicateOutboundCalculation({
          path: { calculation_code: code },
        })
      : warehouseApiRoutesOutboundOrdersDuplicateOutboundOrder({ path: { order_code: code } })

  const addItem = (code: string, body: OutboundOrderItemCreateSchema) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsAddItemToOutboundCalculation({
          path: { calculation_code: code },
          body,
        })
      : warehouseApiRoutesOutboundOrdersAddItemToOutboundOrder({
          path: { order_code: code },
          body,
        })

  const updateItem = (code: string, itemIndex: number, body: OutboundOrderItemCreateSchema) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsUpdateItemInOutboundCalculation({
          path: { calculation_code: code, item_index: itemIndex },
          body,
        })
      : warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder({
          path: { order_code: code, item_index: itemIndex },
          body,
        })

  const removeItem = (code: string, itemIndex: number) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsRemoveItemFromOutboundCalculation({
          path: { calculation_code: code, item_index: itemIndex },
        })
      : warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder({
          path: { order_code: code, item_index: itemIndex },
        })

  const reorderItem = (code: string, itemIndex: number, newIndex: number) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsReorderItemInOutboundCalculation({
          path: { calculation_code: code, item_index: itemIndex },
          body: { new_index: newIndex },
        })
      : warehouseApiRoutesOutboundOrdersReorderItemInOutboundOrder({
          path: { order_code: code, item_index: itemIndex },
          body: { new_index: newIndex },
        })

  /** Bulk: require (or, with null, drop) the same origin country on all items. */
  const setOriginCountry = (code: string, country: string | null) =>
    isCalculation()
      ? warehouseApiRoutesOutboundCalculationsSetOutboundCalculationOriginCountry({
          path: { calculation_code: code },
          body: { country },
        })
      : warehouseApiRoutesOutboundOrdersSetOutboundOrderOriginCountry({
          path: { order_code: code },
          body: { country },
        })

  return {
    isCalculation,
    detailRouteName: () => (isCalculation() ? 'outboundCalculationDetail' : 'outboundOrderDetail'),
    list,
    get,
    create,
    update,
    duplicate,
    addItem,
    updateItem,
    removeItem,
    reorderItem,
    setOriginCountry,
  }
}
