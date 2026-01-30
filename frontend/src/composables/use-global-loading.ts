import { ref } from 'vue'

const isLoading = ref(false)

export const useGlobalLoading = () => {
  const toggle = () => {
    isLoading.value = !isLoading.value
  }

  return {
    isLoading,
    toggle,
  }
}
