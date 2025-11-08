import { useStorage } from '@vueuse/core'
import { useQuasar } from 'quasar'

const isDark = useStorage('theme-dark', false)

export const useDarkmode = () => {
  // Toggle Quasar dark theme
  const $q = useQuasar()

  if ($q?.dark) {
    $q.dark.set(isDark.value)
  }

  const toggle = () => {
    isDark.value = !isDark.value
    $q.dark.set(isDark.value)
  }

  return {
    isDark,
    toggle,
  }
}
