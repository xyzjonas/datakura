import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DocumentTemplatesSettingsTab from '../../DocumentTemplatesSettingsTab.vue'

const mocks = vi.hoisted(() => ({
  notify: vi.fn(),
  confirm: vi.fn(),
  getTargets: vi.fn(),
  getTemplate: vi.fn(),
  getRecords: vi.fn(),
  apply: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesDocumentTemplatesApplyPageSettings: mocks.apply,
  warehouseApiRoutesDocumentTemplatesExportDocumentPdf: vi.fn(),
  warehouseApiRoutesDocumentTemplatesGetDocumentRecords: mocks.getRecords,
  warehouseApiRoutesDocumentTemplatesGetDocumentTargets: mocks.getTargets,
  warehouseApiRoutesDocumentTemplatesGetDocumentTemplate: mocks.getTemplate,
  warehouseApiRoutesDocumentTemplatesResetDocumentTemplate: vi.fn(),
  warehouseApiRoutesDocumentTemplatesUpdateDocumentTemplate: vi.fn(),
}))

vi.mock('quasar', async (importOriginal) => ({
  ...(await importOriginal<typeof import('quasar')>()),
  useQuasar: () => ({
    notify: mocks.notify,
    dialog: () => ({ onOk: (fn: () => void) => mocks.confirm.mockImplementation(fn) }),
  }),
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: (response: { data?: unknown }) => response.data }),
}))

vi.mock('@/composables/use-document-preview', async () => {
  const { ref } = await import('vue')
  return { useDocumentPreview: () => ({ html: ref(''), failed: ref(false), loading: ref(false) }) }
})

const page = {
  margin_top: 12,
  margin_right: 30,
  margin_bottom: 30,
  margin_left: 30,
  font: 'inter',
  logo: null,
}
const pagination = { enabled: true, position: 'top-left' }
const template = {
  target: 'offer',
  label: 'Nabídka',
  is_default: true,
  layout: { header: { title: 'X' }, page, pagination },
  catalog: {},
}

const mountTab = async () => {
  const wrapper = mount(DocumentTemplatesSettingsTab, {
    global: {
      stubs: {
        LayoutEditor: true,
        DocumentPreview: true,
        QSelect: true,
        QSpace: true,
        QBadge: true,
        QItem: true,
        QItemSection: true,
        QBtn: {
          props: ['disable'],
          emits: ['click'],
          template: '<button :disabled="disable" @click="$emit(\'click\')" />',
        },
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('DocumentTemplatesSettingsTab - page settings for all documents', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getTargets.mockResolvedValue({
      data: { data: [{ target: 'offer', label: 'Nabídka', is_default: true }] },
    })
    mocks.getTemplate.mockResolvedValue({ data: { data: template } })
    mocks.getRecords.mockResolvedValue({ data: { data: [] } })
    mocks.apply.mockResolvedValue({
      data: { data: [{ target: 'offer', label: 'Nabídka', is_default: false }] },
    })
  })

  it('sends the viewed page and numbering settings to the API', async () => {
    const wrapper = await mountTab()

    await wrapper.find('[data-test="apply-page"]').trigger('click')
    mocks.confirm()
    await flushPromises()

    expect(mocks.apply).toHaveBeenCalledWith({ body: { page, pagination } })
    expect(mocks.notify).toHaveBeenCalledWith(expect.objectContaining({ type: 'positive' }))
  })

  it('does nothing until the user confirms', async () => {
    const wrapper = await mountTab()

    await wrapper.find('[data-test="apply-page"]').trigger('click')
    await flushPromises()

    expect(mocks.apply).not.toHaveBeenCalled()
  })

  it('does not report success when the API fails', async () => {
    mocks.apply.mockResolvedValue({ error: { detail: 'boom' } })
    const wrapper = await mountTab()

    await wrapper.find('[data-test="apply-page"]').trigger('click')
    mocks.confirm()
    await flushPromises()

    expect(mocks.notify).not.toHaveBeenCalled()
  })
})
