import { useLocalStorage } from '@vueuse/core'

const scannerMode = useLocalStorage('app-setting-scanner-mode', false)

export function useAppSettings() {
  return { scannerMode }
}
