import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useInvoicesQuery() {
  const route = useRoute()
  const router = useRouter()

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

  return {
    page,
    pageSize,
  }
}
