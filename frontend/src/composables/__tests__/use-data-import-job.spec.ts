import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'

import { POLL_INTERVAL_MS, useDataImportJob } from '@/composables/use-data-import-job'

const mocks = vi.hoisted(() => ({
  start: vi.fn(),
  getJob: vi.fn(),
  onResponse: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesDataImportStartDataImport: mocks.start,
  warehouseApiRoutesDataImportGetDataImportJob: mocks.getJob,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: mocks.onResponse }),
}))

const JOB_ID = '5c1e3c6e-9b7e-4c3a-8f57-1c2f7c9a0e11'
const STORAGE_KEY = 'data-import-job-id'

const job = (overrides: Record<string, unknown> = {}) => ({
  data: { data: { job_id: JOB_ID, state: 'running', percent: 10, ...overrides } },
})

const tick = async (ms = POLL_INTERVAL_MS) => {
  await vi.advanceTimersByTimeAsync(ms)
}

const setup = () => {
  const scope = effectScope()
  const api = scope.run(() => useDataImportJob())!
  return { scope, api }
}

describe('useDataImportJob', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    Object.values(mocks).forEach((mock) => mock.mockReset())
    mocks.onResponse.mockImplementation((response: { data?: unknown }) => response.data)
    mocks.start.mockResolvedValue({ data: { data: { job_id: JOB_ID } } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts the job, polls until it succeeds and then stops polling', async () => {
    mocks.getJob
      .mockResolvedValueOnce(job({ state: 'running', percent: 20 }))
      .mockResolvedValueOnce(job({ state: 'running', percent: 70 }))
      .mockResolvedValueOnce(job({ state: 'succeeded', percent: 100 }))
    const { api, scope } = setup()

    await expect(api.start({ products_file: new File([], 'p.json') })).resolves.toBe(true)
    await vi.advanceTimersByTimeAsync(0)
    expect(api.status.value?.percent).toBe(20)
    expect(api.running.value).toBe(true)
    expect(mocks.getJob).toHaveBeenCalledWith({ path: { job_id: JOB_ID } })

    await tick()
    expect(api.status.value?.percent).toBe(70)
    await tick()
    expect(api.status.value?.state).toBe('succeeded')
    expect(api.running.value).toBe(false)

    await tick(10 * POLL_INTERVAL_MS)
    expect(mocks.getJob).toHaveBeenCalledTimes(3)
    scope.stop()
  })

  it('stops polling on failure and exposes the error', async () => {
    mocks.getJob.mockResolvedValue(job({ state: 'failed', error: 'boom' }))
    const { api, scope } = setup()

    await api.start({})
    await vi.advanceTimersByTimeAsync(0)
    await tick(5 * POLL_INTERVAL_MS)

    expect(api.status.value?.error).toBe('boom')
    expect(api.running.value).toBe(false)
    expect(mocks.getJob).toHaveBeenCalledTimes(1)
    scope.stop()
  })

  it('keeps polling while the job is pending', async () => {
    mocks.getJob.mockResolvedValue(job({ state: 'pending', percent: 0 }))
    const { api, scope } = setup()

    await api.start({})
    await vi.advanceTimersByTimeAsync(0)
    await tick(3 * POLL_INTERVAL_MS)

    expect(mocks.getJob).toHaveBeenCalledTimes(4)
    expect(api.running.value).toBe(true)
    scope.stop()
  })

  it('does not watch anything when the start request fails', async () => {
    mocks.onResponse.mockReturnValue(undefined)
    const { api, scope } = setup()

    await expect(api.start({})).resolves.toBe(false)

    expect(api.watching.value).toBe(false)
    expect(api.running.value).toBe(false)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    expect(mocks.getJob).not.toHaveBeenCalled()
    scope.stop()
  })

  it('resumes a job stored before a page reload', async () => {
    localStorage.setItem(STORAGE_KEY, JOB_ID)
    mocks.getJob.mockResolvedValueOnce(job({ percent: 40 })).mockResolvedValue(
      job({ state: 'succeeded', percent: 100 }),
    )

    const { api, scope } = setup()
    await vi.advanceTimersByTimeAsync(0)

    expect(mocks.start).not.toHaveBeenCalled()
    expect(api.status.value?.percent).toBe(40)
    await tick()
    expect(api.status.value?.state).toBe('succeeded')
    scope.stop()
  })

  it('stopWatching forgets the job and cancels polling', async () => {
    mocks.getJob.mockResolvedValue(job({ state: 'pending', percent: 0 }))
    const { api, scope } = setup()
    await api.start({})
    await vi.advanceTimersByTimeAsync(0)

    api.stopWatching()
    await tick(5 * POLL_INTERVAL_MS)

    expect(api.status.value).toBeNull()
    expect(api.watching.value).toBe(false)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    expect(mocks.getJob).toHaveBeenCalledTimes(1)
    scope.stop()
  })

  it('gives up after repeated poll errors', async () => {
    mocks.getJob.mockResolvedValue({ data: undefined })
    const { api, scope } = setup()
    await api.start({})
    await vi.advanceTimersByTimeAsync(0)
    await tick(10 * POLL_INTERVAL_MS)

    expect(mocks.getJob).toHaveBeenCalledTimes(3)
    expect(api.watching.value).toBe(false)
    scope.stop()
  })

  it('recovers from a single failed poll', async () => {
    mocks.getJob
      .mockResolvedValueOnce({ data: undefined })
      .mockResolvedValue(job({ state: 'succeeded', percent: 100 }))
    const { api, scope } = setup()
    await api.start({})
    await vi.advanceTimersByTimeAsync(0)
    await tick()

    expect(api.status.value?.state).toBe('succeeded')
    scope.stop()
  })

  it('stops polling when the owning scope is disposed', async () => {
    mocks.getJob.mockResolvedValue(job({ state: 'running' }))
    const { api, scope } = setup()
    await api.start({})
    await vi.advanceTimersByTimeAsync(0)

    scope.stop()
    await tick(5 * POLL_INTERVAL_MS)

    expect(mocks.getJob).toHaveBeenCalledTimes(1)
  })
})
