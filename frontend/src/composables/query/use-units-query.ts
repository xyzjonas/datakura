import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryUnits() {
  const route = useRoute()
  const router = useRouter()

  const search = computed<string>({
    get() {
      const raw = route.query.uom_search
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string) {
      const query = { ...route.query }
      if (val) {
        query.uom_search = val
      } else {
        delete query.uom_search
      }
      router.push({ query })
    },
  })

  const page = computed<number>({
    get() {
      const raw = route.query.uom_page
      if (raw) {
        return +raw
      }
      return 1
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.uom_page = `${val}`
      } else {
        delete query.uom_page
      }
      router.push({ query })
    },
  })

  const pageSize = computed<number>({
    get() {
      const raw = route.query.uom_page_size
      if (raw) {
        return +raw
      }
      return 20
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.uom_page_size = `${val}`
      } else {
        delete query.uom_page_size
      }
      router.push({ query })
    },
  })

  return {
    search,
    page,
    pageSize,
  }
}
