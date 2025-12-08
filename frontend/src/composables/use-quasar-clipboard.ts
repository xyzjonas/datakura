import { useClipboard } from '@vueuse/core'
import { useQuasar } from 'quasar'

export const useQuasarClipboard = () => {
  const { copy: copyImpl } = useClipboard()
  const $q = useQuasar()

  function copy(text: string) {
    copyImpl(text)
    $q.notify({
      type: 'positive',
      message: text,
      caption: 'Zkopírováno  do schránky',
      timeout: 1000,
    })
  }

  return {
    copy,
  }
}
