import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MinimumProfitSetting from '@/components/settings/MinimumProfitSetting.vue'
import { useMinimumProfit } from '@/composables/use-minimum-profit'

const mocks = vi.hoisted(() => ({ getSettings: vi.fn(), updateSettings: vi.fn() }))

vi.mock('@/client', () => ({
  warehouseApiRoutesSettingsGetGlobalSettings: mocks.getSettings,
  warehouseApiRoutesSettingsUpdateGlobalSettings: mocks.updateSettings,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: (response: { data?: unknown }) => response.data }),
}))

const mountComponent = () =>
  mount(MinimumProfitSetting, {
    global: {
      stubs: {
        QCard: { template: '<div><slot /></div>' },
        QBtnToggle: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<div><button data-test="to-margin" @click="$emit(\'update:modelValue\', \'margin\')" /><button data-test="to-markup" @click="$emit(\'update:modelValue\', \'markup\')" /></div>',
        },
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

const saveButton = (wrapper: ReturnType<typeof mountComponent>) =>
  wrapper.findAll('button').find((b) => b.text() === 'uložit')!

describe('MinimumProfitSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getSettings.mockResolvedValue({ data: { data: { minimum_markup_percent: 25 } } })
    mocks.updateSettings.mockImplementation(async ({ body }) => ({
      data: { data: { minimum_markup_percent: body.minimum_markup_percent } },
    }))
  })

  it('loads the stored markup, shares it app-wide and keeps save disabled', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('25')
    expect(wrapper.get('[data-test="profit-equivalent"]').text()).toContain('marži 20 %')
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()
    expect(useMinimumProfit().minimumMarkupPercent.value).toBe(25)
  })

  it('switching to marže shows the equivalent value and does not change what is saved', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.get('[data-test="to-margin"]').trigger('click')

    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('20')
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()
  })

  it('converts marže input into the stored markup', async () => {
    const wrapper = mountComponent()
    await flushPromises()
    await wrapper.get('[data-test="to-margin"]').trigger('click')

    await wrapper.get('input').setValue('50')
    await saveButton(wrapper).trigger('click')
    await flushPromises()

    expect(mocks.updateSettings).toHaveBeenCalledWith({ body: { minimum_markup_percent: 100 } })
    expect(useMinimumProfit().minimumMarkupPercent.value).toBe(100)
  })

  it.each(['-5', '100', '150'])('refuses invalid marže %s', async (value) => {
    const wrapper = mountComponent()
    await flushPromises()
    await wrapper.get('[data-test="to-margin"]').trigger('click')

    await wrapper.get('input').setValue(value)

    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()
  })

  it('saves a markup directly and allows turning the guard off with 0', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    await wrapper.get('input').setValue('0')
    await saveButton(wrapper).trigger('click')
    await flushPromises()

    expect(mocks.updateSettings).toHaveBeenCalledWith({ body: { minimum_markup_percent: 0 } })
  })
})
