import { useLocalStorage } from '@vueuse/core'
import { useQuasar } from 'quasar'
import { watch } from 'vue'

const isDark = useLocalStorage('theme-dark', false)

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

  watch(isDark, () => $q.dark.set(isDark.value))

  return {
    isDark,
    toggle,
  }
}
