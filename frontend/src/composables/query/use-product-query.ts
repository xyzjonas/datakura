import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryProduct() {
  const route = useRoute()
  const router = useRouter()

  const location = computed<string | undefined>({
    get() {
      const raw = route.query.location
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string | undefined) {
      const query = { ...route.query }
      if (val) {
        query.location = val
      } else {
        delete query.location
      }
      router.replace({ query })
    },
  })

  const locationSearch = computed<string>({
    get() {
      const raw = route.query.locationSearch
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string) {
      const query = { ...route.query }
      if (val) {
        query.locationSearch = val
      } else {
        delete query.locationSearch
      }
      router.replace({ query })
    },
  })

  const itemSearch = computed<string>({
    get() {
      const raw = route.query.itemSearch
      if (raw) {
        return `${raw}`
      }
      return ''
    },
    set(val: string) {
      const query = { ...route.query }
      if (val) {
        query.itemSearch = val
      } else {
        delete query.itemSearch
      }
      router.replace({ query })
    },
  })

  return {
    location,
    locationSearch,
    itemSearch,
  }
}
