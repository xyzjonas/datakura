import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryTypes() {
  const route = useRoute()
  const router = useRouter()

  const search = computed<string>({
    get() {
      const raw = route.query.type_search
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string) {
      const query = { ...route.query }
      if (val) {
        query.type_search = val
      } else {
        delete query.type_search
      }
      router.push({ query })
    },
  })

  const page = computed<number>({
    get() {
      const raw = route.query.type_page
      if (raw) {
        return +raw
      }
      return 1
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.type_page = `${val}`
      } else {
        delete query.type_page
      }
      router.push({ query })
    },
  })

  const pageSize = computed<number>({
    get() {
      const raw = route.query.type_page_size
      if (raw) {
        return +raw
      }
      return 20
    },
    set(val: number) {
      const query = { ...route.query }
      if (val) {
        query.type_page_size = `${val}`
      } else {
        delete query.type_page_size
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
