import { useLocalStorage } from '@vueuse/core'

const isOpened = useLocalStorage('main-layout-drawer-opened', true)

export const useDrawer = () => {
  const open = () => {
    isOpened.value = true
  }

  const close = () => {
    isOpened.value = false
  }

  const toggle = () => {
    isOpened.value = !isOpened.value
  }

  return {
    isOpened,
    open,
    close,
    toggle,
  }
}
