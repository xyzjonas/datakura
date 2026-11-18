import type { BaseOrder } from '@/client'

type ParentOrder = Pick<BaseOrder, 'type' | 'customer' | 'supplier'>

/**
 * Receipts (příjemky) belong to a purchase order, a manufacturing order or - when
 * goods are taken back from a customer ("vratka") - to the sales order.
 */
export const parentOrderRouteName = (order: Pick<BaseOrder, 'type'>): string => {
  switch (order.type) {
    case 'Outbound':
      return 'outboundOrderDetail'
    case 'Manufacturing':
      return 'manufacturingOrderDetail'
    default:
      return 'inboundOrderDetail'
  }
}

/** The other side of the deal: the supplier of a purchase, the customer of a sale. */
export const parentOrderPartner = (order: ParentOrder) =>
  order.type === 'Outbound' ? order.customer : order.supplier

export const parentOrderPartnerLabel = (order: Pick<BaseOrder, 'type'>): string =>
  order.type === 'Outbound' ? 'Odběratel' : 'Dodavatel'
