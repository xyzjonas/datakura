import {
  warehouseApiRoutesDocumentTemplatesPreviewDocument,
  type DocumentTarget,
  type TemplateErrorSchema,
} from '@/client'
import { useDebounceFn } from '@vueuse/core'
import { ref, watch, type Ref } from 'vue'

/**
 * Live HTML preview of a (draft) template over a record. Re-renders (debounced) whenever
 * the template, the record or the target change. The last successful `html` is kept while
 * the draft is broken, so typing never blanks the preview.
 */
export const useTemplatePreview = (
  target: Ref<DocumentTarget | undefined>,
  recordCode: Ref<string | undefined>,
  content: Ref<string>,
  delayMs = 400,
) => {
  const html = ref('')
  const error = ref<TemplateErrorSchema | null>(null)
  const loading = ref(false)
  let latestRequest = 0

  const render = async () => {
    if (!target.value || !recordCode.value) {
      html.value = ''
      error.value = null
      loading.value = false
      return
    }
    const request = ++latestRequest
    loading.value = true
    try {
      const response = await warehouseApiRoutesDocumentTemplatesPreviewDocument({
        path: { target: target.value },
        body: { record_code: recordCode.value, content: content.value },
      })
      if (request !== latestRequest) return // a newer render is already on its way
      const preview = response.data?.data
      if (!response.response.ok || !preview) {
        error.value = { message: 'Náhled se nepodařilo načíst', line: null }
      } else if (preview.error) {
        error.value = preview.error
      } else {
        html.value = preview.html ?? ''
        error.value = null
      }
    } catch {
      if (request === latestRequest) {
        error.value = { message: 'Náhled se nepodařilo načíst', line: null }
      }
    } finally {
      if (request === latestRequest) loading.value = false
    }
  }

  const debounced = useDebounceFn(render, delayMs)
  watch(content, () => void debounced())
  // another document: nothing of the previous one may linger
  watch(target, () => (html.value = ''))
  // target / record switches are not typing - show them right away
  watch([target, recordCode], () => void render(), { immediate: true })

  return { html, error, loading, refresh: render }
}
