import { warehouseApiRoutesDocumentTemplatesPreviewDocument, type DocumentTarget } from '@/client'
import type { DocumentLayout } from '@/components/settings/document-templates/types'
import { useDebounceFn } from '@vueuse/core'
import { ref, watch, type Ref } from 'vue'

/**
 * Live HTML preview of a (draft) layout over a record. Re-renders (debounced) whenever the
 * layout changes, right away when the record or the target change. The last successful
 * `html` is kept while a render fails, so editing never blanks the preview.
 */
export const useDocumentPreview = (
  target: Ref<DocumentTarget | undefined>,
  recordCode: Ref<string | undefined>,
  layout: Ref<DocumentLayout | undefined>,
  delayMs = 400,
) => {
  const html = ref('')
  const failed = ref(false)
  const loading = ref(false)
  let latestRequest = 0

  const render = async () => {
    if (!target.value || !recordCode.value || !layout.value) {
      html.value = ''
      failed.value = false
      loading.value = false
      return
    }
    const request = ++latestRequest
    loading.value = true
    try {
      const response = await warehouseApiRoutesDocumentTemplatesPreviewDocument({
        path: { target: target.value },
        body: { record_code: recordCode.value, layout: layout.value },
      })
      if (request !== latestRequest) return // a newer render is already on its way
      const preview = response.data?.data
      if (!response.response.ok || preview === undefined) {
        failed.value = true
      } else {
        html.value = preview
        failed.value = false
      }
    } catch {
      if (request === latestRequest) failed.value = true
    } finally {
      if (request === latestRequest) loading.value = false
    }
  }

  const debounced = useDebounceFn(render, delayMs)
  watch(layout, () => void debounced(), { deep: true })
  // another document: nothing of the previous one may linger
  watch(target, () => (html.value = ''))
  // target / record switches are not editing - show them right away
  watch([target, recordCode], () => void render(), { immediate: true })

  return { html, failed, loading, refresh: render }
}
