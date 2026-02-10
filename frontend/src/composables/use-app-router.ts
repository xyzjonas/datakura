import { useRouter } from 'vue-router'

export const useAppRouter = () => {
  const router = useRouter()
  const goToCustomer = (code: string) => {
    router.push({ name: 'customerDetail', params: { customerCode: code } })
  }

  const goToWarehouseOrderIn = (code: string) => {
    router.push({ name: 'warehouseInboundOrderDetail', params: { code } })
  }

  const goToOrderIn = (code: string) => {
    router.push({ name: 'incomingOrderDetail', params: { code } })
  }

  const goToProduct = (code: string) => {
    router.push({ name: 'productDetail', params: { productCode: code } })
  }

  const goToCreditNote = (code: string) => {
    router.push({ name: 'creditNoteToSupplier', params: { code } })
  }

  return {
    goToCustomer,
    goToOrderIn,
    goToWarehouseOrderIn,
    goToProduct,
    goToCreditNote,
  }
}
