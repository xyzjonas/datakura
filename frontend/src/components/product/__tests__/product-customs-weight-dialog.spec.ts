import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProductCustomsWeightDialog from '../ProductCustomsWeightDialog.vue'

installQuasarPlugin()

const updateMock = vi.hoisted(() => vi.fn())
vi.mock('@/client', () => ({
  warehouseApiRoutesProductUpdateProductCustomsWeight: updateMock,
}))
vi.mock('quasar', async (importOriginal) => ({
  ...(await importOriginal<typeof import('quasar')>()),
  useQuasar: () => ({ notify: vi.fn() }),
}))
vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: (r: { data?: unknown }) => r.data }),
}))

const product = { code: 'PRD-1', name: 'Produkt', unit_weight: 0, customs_declaration_group: null }

const mountDialog = () =>
  mount(ProductCustomsWeightDialog, {
    props: { show: true, product },
    global: {
      stubs: {
        QDialog: { template: '<div><slot /></div>' },
        QCard: { template: '<div><slot /></div>' },
        QForm: { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
        QInput: {
          props: ['modelValue', 'label'],
          emits: ['update:modelValue'],
          template:
            '<input :data-test="label" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        QBtn: { template: '<button><slot /></button>' },
        QSeparator: { template: '<hr />' },
      },
    },
  })

describe('ProductCustomsWeightDialog', () => {
  beforeEach(() => updateMock.mockReset())

  it('saves weight and customs code via SDK and emits saved', async () => {
    const saved = { code: 'PRD-1', unit_weight: 12.5 }
    updateMock.mockResolvedValue({ data: { data: saved } })
    const wrapper = mountDialog()

    await wrapper.find('[data-test="Váha jednotky (g)"]').setValue('12.5')
    await wrapper.find('[data-test="Celní nomenklatura"]').setValue('8471 30')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(updateMock).toHaveBeenCalledWith({
      path: { product_code: 'PRD-1' },
      body: { unit_weight: 12.5, customs_declaration_group: '8471 30' },
    })
    expect(wrapper.emitted('saved')?.[0]?.[0]).toEqual(saved)
  })

  it('sends null for a blank customs code', async () => {
    updateMock.mockResolvedValue({ data: { data: {} } })
    const wrapper = mountDialog()

    await wrapper.find('[data-test="Váha jednotky (g)"]').setValue('3')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(updateMock.mock.calls[0]![0].body.customs_declaration_group).toBeNull()
  })
})
