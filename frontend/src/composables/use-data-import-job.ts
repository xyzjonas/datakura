import {
  warehouseApiRoutesDataImportGetDataImportJob,
  warehouseApiRoutesDataImportStartDataImport,
  type DataImportJobStatusSchema,
  type WarehouseApiRoutesDataImportStartDataImportData,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useLocalStorage } from '@vueuse/core'
import { computed, onScopeDispose, ref } from 'vue'

export const POLL_INTERVAL_MS = 1000
const MAX_CONSECUTIVE_POLL_ERRORS = 3
const STORAGE_KEY = 'data-import-job-id'

const isActive = (status: DataImportJobStatusSchema | null) =>
  status?.state === 'pending' || status?.state === 'running'

/**
 * Starts the asynchronous data import and follows the job by polling its state.
 * The job id survives a page reload, so a long import can be picked up again.
 */
export const useDataImportJob = () => {
  const { onResponse } = useApi()

  const jobId = useLocalStorage<string | null>(STORAGE_KEY, null)
  const status = ref<DataImportJobStatusSchema | null>(null)
  const starting = ref(false)
  const watching = computed(() => jobId.value !== null)
  const running = computed(() => starting.value || (watching.value && isActive(status.value)))

  let timer: ReturnType<typeof setTimeout> | undefined
  let failedPolls = 0

  const clearTimer = () => {
    clearTimeout(timer)
    timer = undefined
  }

  const poll = async () => {
    const id = jobId.value
    if (!id) {
      return
    }
    const response = await warehouseApiRoutesDataImportGetDataImportJob({
      path: { job_id: id },
    })
    const data = onResponse(response, { hideNotification: failedPolls + 1 < MAX_CONSECUTIVE_POLL_ERRORS })
    if (jobId.value !== id) {
      return // stopped / replaced while the request was in flight
    }

    if (data) {
      failedPolls = 0
      status.value = data.data
    } else if (++failedPolls >= MAX_CONSECUTIVE_POLL_ERRORS) {
      jobId.value = null
      return
    }

    if (data === undefined || isActive(status.value)) {
      timer = setTimeout(poll, POLL_INTERVAL_MS)
    }
  }

  const follow = () => {
    clearTimer()
    failedPolls = 0
    void poll()
  }

  const start = async (body: WarehouseApiRoutesDataImportStartDataImportData['body']) => {
    starting.value = true
    try {
      const response = await warehouseApiRoutesDataImportStartDataImport({ body })
      const data = onResponse(response)
      if (!data) {
        return false
      }
      status.value = { job_id: data.data.job_id, state: 'pending' }
      jobId.value = data.data.job_id
      follow()
      return true
    } finally {
      starting.value = false
    }
  }

  const stopWatching = () => {
    clearTimer()
    jobId.value = null
    status.value = null
  }

  // pick up a job from before a reload
  if (jobId.value) {
    follow()
  }
  onScopeDispose(clearTimer)

  return { status, running, watching, start, stopWatching }
}
