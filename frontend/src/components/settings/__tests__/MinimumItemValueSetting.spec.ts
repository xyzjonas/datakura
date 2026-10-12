import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MinimumItemValueSetting from '@/components/settings/MinimumItemValueSetting.vue'

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
  mount(MinimumItemValueSetting, {
    global: {
      stubs: {
        QCard: { template: '<div><slot /></div>' },
        QInput: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" />',
        },
        QBtn: {
          props: ['label', 'disable'],
          emits: ['click'],
          template: '<button :disabled="disable" @click="$emit(\'click\')">{{ label }}</button>',
        },
      },
    },
  })

describe('MinimumItemValueSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getSettings.mockResolvedValue({ data: { data: { minimum_item_value: 5 } } })
  })

  it('loads the stored value and keeps save disabled until it changes', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('5')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('saves the changed value', async () => {
    mocks.updateSettings.mockResolvedValue({ data: { data: { minimum_item_value: 20 } } })
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.find('input').setValue('20')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(mocks.updateSettings).toHaveBeenCalledWith({ body: { minimum_item_value: 20 } })
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('does not allow saving a negative value', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.find('input').setValue('-1')

    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })
})
