import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import type { DocumentTarget } from '@/client'
import type { DocumentLayout } from '@/components/settings/document-templates/types'
import { useDocumentPreview } from '../use-document-preview'

const mocks = vi.hoisted(() => ({ preview: vi.fn() }))

vi.mock('@/client', () => ({
  warehouseApiRoutesDocumentTemplatesPreviewDocument: mocks.preview,
}))

const ok = (html: string) => ({ response: { ok: true }, data: { success: true, data: html } })
const layoutOf = (title: string) => ({ header: { title } }) as unknown as DocumentLayout

const setup = (record: string | null = 'REC-1') => {
  const target = ref<DocumentTarget | undefined>('offer')
  const recordCode = ref<string | undefined>(record ?? undefined)
  const layout = ref<DocumentLayout | undefined>(layoutOf('v1'))
  const scope = effectScope()
  const preview = scope.run(() => useDocumentPreview(target, recordCode, layout, 400))!
  return { target, recordCode, layout, preview, scope }
}

const titleOf = (layout: DocumentLayout) => layout.header.title

describe('useDocumentPreview', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocks.preview.mockReset()
    mocks.preview.mockImplementation(async ({ body }) => ok(`<p>${titleOf(body.layout)}</p>`))
  })
  afterEach(() => vi.useRealTimers())

  it('renders right away for the initial record', async () => {
    const { preview, scope } = setup()
    await flushPromises()

    expect(mocks.preview).toHaveBeenCalledWith({
      path: { target: 'offer' },
      body: { record_code: 'REC-1', layout: layoutOf('v1') },
    })
    expect(preview.html.value).toBe('<p>v1</p>')
    expect(preview.failed.value).toBe(false)
    scope.stop()
  })

  it('does not render without a record or a layout', async () => {
    const { preview, layout, scope } = setup(null)
    await flushPromises()
    expect(mocks.preview).not.toHaveBeenCalled()

    layout.value = undefined
    await vi.advanceTimersByTimeAsync(500)
    expect(mocks.preview).not.toHaveBeenCalled()
    expect(preview.html.value).toBe('')
    scope.stop()
  })

  it('debounces edits of the layout (also nested ones)', async () => {
    const { layout, preview, scope } = setup()
    await flushPromises()
    mocks.preview.mockClear()

    layout.value!.header.title = 'v2'
    await nextTick()
    layout.value!.header.title = 'v3'
    await vi.advanceTimersByTimeAsync(399)
    expect(mocks.preview).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(2)

    expect(mocks.preview).toHaveBeenCalledTimes(1)
    expect(preview.html.value).toBe('<p>v3</p>')
    scope.stop()
  })

  it('renders a record switch immediately', async () => {
    const { recordCode, scope } = setup()
    await flushPromises()
    mocks.preview.mockClear()

    recordCode.value = 'REC-2'
    await flushPromises()

    expect(mocks.preview).toHaveBeenCalledTimes(1)
    expect(mocks.preview.mock.calls[0]![0].body.record_code).toBe('REC-2')
    scope.stop()
  })

  it('keeps the last page when a render fails and recovers afterwards', async () => {
    const { layout, preview, scope } = setup()
    await flushPromises()
    mocks.preview.mockResolvedValueOnce({ response: { ok: false }, data: undefined })

    layout.value!.header.title = 'broken'
    await vi.advanceTimersByTimeAsync(500)
    expect(preview.failed.value).toBe(true)
    expect(preview.html.value).toBe('<p>v1</p>')

    layout.value!.header.title = 'fixed'
    await vi.advanceTimersByTimeAsync(500)
    expect(preview.failed.value).toBe(false)
    expect(preview.html.value).toBe('<p>fixed</p>')
    scope.stop()
  })

  it('treats a rejected request as a failure', async () => {
    mocks.preview.mockRejectedValueOnce(new Error('network'))
    const { preview, scope } = setup()
    await flushPromises()

    expect(preview.failed.value).toBe(true)
    expect(preview.loading.value).toBe(false)
    scope.stop()
  })

  it('ignores a stale response that arrives after a newer one', async () => {
    let releaseFirst: (v: unknown) => void = () => {}
    mocks.preview.mockImplementationOnce(() => new Promise((resolve) => (releaseFirst = resolve)))
    const { recordCode, preview, scope } = setup()

    recordCode.value = 'REC-2'
    await flushPromises()
    expect(preview.html.value).toBe('<p>v1</p>')
    releaseFirst(ok('<p>stale</p>'))
    await flushPromises()

    expect(preview.html.value).toBe('<p>v1</p>')
    scope.stop()
  })

  it('drops the page of the previous document when the target changes', async () => {
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
