import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryProducts() {
  const route = useRoute()
  const router = useRouter()

  const search = computed<string>({
    get() {
      const raw = route.query.search
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string) {
      const query = { ...route.query }
      if (val) {
        query.search = val
      } else {
        delete query.search
      }
      router.push({ query })
    },
  })

  const page = computed<number>({
    get() {
      const raw = route.query.page
      if (raw) {
        return +raw
      }
      return 1
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.page = `${val}`
      } else {
        delete query.page
      }
      router.push({ query })
    },
  })

  const pageSize = computed<number>({
    get() {
      const raw = route.query.page_size
      if (raw) {
        return +raw
      }
      return 20
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.page_size = `${val}`
      } else {
        delete query.page_size
      }
      router.push({ query })
    },
  })

  const productType = computed<string | null>({
    get() {
      const raw = route.query.product_type
      if (raw) {
        return `${raw}`
      }
      return null
    },
    set(val: string | null) {
      const query = { ...route.query }
      if (val) {
        query.product_type = val
      } else {
        delete query.product_type
      }
      router.push({ query })
    },
  })

  const productGroup = computed<string | null>({
    get() {
      const raw = route.query.product_group
      if (raw) {
        return `${raw}`
      }
      return null
    },
    set(val: string | null) {
      const query = { ...route.query }
      if (val) {
        query.product_group = val
      } else {
        delete query.product_group
      }
      router.push({ query })
    },
  })

  const stockProductCode = computed<string | null>({
    get() {
      const raw = route.query.stock_product_code
      if (raw) {
        return `${raw}`
      }
      return null
    },
    set(val: string | null) {
      const query = { ...route.query }
      if (val) {
        query.stock_product_code = val
      } else {
        delete query.stock_product_code
      }
      router.push({ query })
    },
  })

  return {
    search,
    page,
    pageSize,
    productType,
    productGroup,
    stockProductCode,
  }
}
