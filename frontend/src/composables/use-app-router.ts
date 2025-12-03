import { useRouter } from 'vue-router'

export const useAppRouter = () => {
  const router = useRouter()
  const goToCustomer = (code: string) => {
    router.push({ name: 'customerDetail', params: { customerCode: code } })
  }

  const goToWarehouseOrderIn = (code: string) => {
    router.push({ name: 'warehouseInboundOrderDetail', params: { code } })
  }

  return {
    goToCustomer,
    goToWarehouseOrderIn,
  }
}
