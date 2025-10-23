import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useQueryWarehouse() {
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

  return {
    location,
  }
}
