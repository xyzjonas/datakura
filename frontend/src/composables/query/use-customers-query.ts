import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryCustomers() {
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
      // router.replace({ query })
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
      // router.replace({ query })
    },
  })

  const pageSize = computed<number>({
    get() {
      const raw = route.query.page_size
      if (raw) {
        return Number(raw)
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
      // router.replace({ query })
    },
  })

  return {
    search,
    page,
    pageSize,
  }
}
