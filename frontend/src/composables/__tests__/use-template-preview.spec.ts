import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import type { DocumentTarget } from '@/client'
import { useTemplatePreview } from '../use-template-preview'

const mocks = vi.hoisted(() => ({ preview: vi.fn() }))

vi.mock('@/client', () => ({
  warehouseApiRoutesDocumentTemplatesPreviewDocument: mocks.preview,
}))

const ok = (html: string) => ({
  response: { ok: true },
  data: { success: true, data: { html, error: null } },
})
const templateError = (message: string, line: number) => ({
  response: { ok: true },
  data: { success: true, data: { html: null, error: { message, line } } },
})

const setup = (initial = 'v1', record: string | null = 'REC-1') => {
  const target = ref<DocumentTarget | undefined>('offer')
  const recordCode = ref<string | undefined>(record ?? undefined)
  const content = ref(initial)
  const scope = effectScope()
  const preview = scope.run(() => useTemplatePreview(target, recordCode, content, 400))!
  return { target, recordCode, content, preview, scope }
}

describe('useTemplatePreview', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocks.preview.mockReset()
    mocks.preview.mockImplementation(async ({ body }) => ok(`<p>${body.content}</p>`))
  })
  afterEach(() => vi.useRealTimers())

  it('renders right away for the initial record', async () => {
    const { preview, scope } = setup()
    await flushPromises()

    expect(mocks.preview).toHaveBeenCalledWith({
      path: { target: 'offer' },
      body: { record_code: 'REC-1', content: 'v1' },
    })
    expect(preview.html.value).toBe('<p>v1</p>')
    expect(preview.error.value).toBeNull()
    scope.stop()
  })

  it('does not render without a record', async () => {
    const { preview, scope } = setup('v1', null)
    await flushPromises()

    expect(mocks.preview).not.toHaveBeenCalled()
    expect(preview.html.value).toBe('')
    scope.stop()
  })

  it('debounces typing into a single request', async () => {
    const { content, scope } = setup()
    await flushPromises()
    mocks.preview.mockClear()

    content.value = 'a'
    await nextTick()
    vi.advanceTimersByTime(200)
    content.value = 'ab'
    await nextTick()
    vi.advanceTimersByTime(200)
    expect(mocks.preview).not.toHaveBeenCalled()
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(mocks.preview).toHaveBeenCalledTimes(1)
    expect(mocks.preview.mock.calls[0]![0].body.content).toBe('ab')
    scope.stop()
  })

  it('keeps the last good html while the draft is broken', async () => {
    const { content, preview, scope } = setup()
    await flushPromises()
    mocks.preview.mockResolvedValueOnce(templateError('unclosed', 3))

    content.value = '{{ oops'
    await nextTick()
    vi.advanceTimersByTime(400)
    await flushPromises()

    expect(preview.html.value).toBe('<p>v1</p>')
    expect(preview.error.value).toEqual({ message: 'unclosed', line: 3 })

    content.value = 'fixed'
    await nextTick()
    vi.advanceTimersByTime(400)
    await flushPromises()

    expect(preview.html.value).toBe('<p>fixed</p>')
    expect(preview.error.value).toBeNull()
    scope.stop()
  })

  it('ignores a stale response arriving after a newer one', async () => {
    let releaseSlow: (v: unknown) => void = () => {}
    const { recordCode, preview, scope } = setup()
    await flushPromises()
    mocks.preview.mockImplementationOnce(() => new Promise((resolve) => (releaseSlow = resolve)))

    recordCode.value = 'REC-SLOW'
    await nextTick()
    recordCode.value = 'REC-FAST'
    await flushPromises()
    expect(preview.html.value).toBe('<p>v1</p>')

    releaseSlow(ok('<p>stale</p>'))
    await flushPromises()

    expect(preview.html.value).toBe('<p>v1</p>')
    expect(preview.loading.value).toBe(false)
    scope.stop()
  })

  it.each([
    ['http failure', () => Promise.resolve({ response: { ok: false }, data: undefined })],
    ['network failure', () => Promise.reject(new Error('offline'))],
  ])('reports a %s as an error', async (_name, failing) => {
    mocks.preview.mockImplementation(failing)
    const { preview, scope } = setup()
    await flushPromises()

    expect(preview.error.value?.message).toContain('Náhled se nepodařilo načíst')
    expect(preview.loading.value).toBe(false)
    scope.stop()
  })

  it('clears the previous document when the target changes', async () => {
    const { target, recordCode, preview, scope } = setup()
    await flushPromises()
    expect(preview.html.value).not.toBe('')

    recordCode.value = undefined
    target.value = 'issue_note'
    await flushPromises()

    expect(preview.html.value).toBe('')
    scope.stop()
  })
})
