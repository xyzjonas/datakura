import { ref } from 'vue'
import {
  warehouseApiRoutesWarehouseBarcodeLookup,
  type BarcodeLookupResponse,
} from '@/client'
import { useApi } from './use-api'

export function useBarcodeLookup() {
  const { onResponse } = useApi()
  const loading = ref(false)
  const error = ref<string | null>(null)

  const lookup = async (
    barcode: string,
    productCode?: string
  ): Promise<BarcodeLookupResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await warehouseApiRoutesWarehouseBarcodeLookup({
        body: {
          barcode,
          product_code: productCode ?? null,
        },
      })

      const data = onResponse(response)
      if (!data || typeof data !== 'object' || !('data' in data)) {
        return null
      }
      return (data.data as BarcodeLookupResponse) ?? null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    lookup,
    loading,
    error,
  }
}
