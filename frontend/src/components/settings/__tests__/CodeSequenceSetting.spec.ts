import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CodeSequenceSetting from '@/components/settings/CodeSequenceSetting.vue'

const mocks = vi.hoisted(() => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesSettingsGetGlobalSettings: mocks.getSettings,
  warehouseApiRoutesSettingsUpdateGlobalSettings: mocks.updateSettings,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

const mountComponent = () =>
  mount(CodeSequenceSetting, {
    global: {
      stubs: {
        QCard: { template: '<div><slot /></div>' },
        QSelect: {
          props: ['modelValue', 'options'],
          emits: ['update:modelValue'],
          template:
            '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
        },
        QBtn: {
          props: ['label', 'disable'],
          emits: ['click'],
          template: '<button :disabled="disable" @click="$emit(\'click\')">{{ label }}</button>',
        },
      },
    },
  })

describe('CodeSequenceSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getSettings.mockResolvedValue({ data: { data: { code_sequence: 'monthly' } } })
  })

  it('loads the stored value and keeps save disabled until it changes', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect((wrapper.find('select').element as HTMLSelectElement).value).toBe('monthly')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('saves only the code sequence', async () => {
    mocks.updateSettings.mockResolvedValue({ data: { data: { code_sequence: 'yearly' } } })
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.find('select').setValue('yearly')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(mocks.updateSettings).toHaveBeenCalledWith({ body: { code_sequence: 'yearly' } })
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('does not save when the request fails', async () => {
    mocks.updateSettings.mockResolvedValue({ data: undefined })
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.find('select').setValue('yearly')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
  })
})
