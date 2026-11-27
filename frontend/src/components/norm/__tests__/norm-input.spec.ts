import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NormInput from '../NormInput.vue'

installQuasarPlugin()

const mountInput = (type: string | null, code: string | null) =>
  mount(NormInput, {
    props: { type: type as never, code },
    global: {
      stubs: {
        QSelect: {
          props: ['modelValue', 'options'],
          template: '<div data-test="norm-type">{{ options.join(",") }}</div>',
        },
        QInput: {
          props: ['modelValue', 'disable'],
          emits: ['update:modelValue'],
          template:
            '<input data-test="norm-code" :value="modelValue" :disabled="disable" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
      },
    },
  })

describe('NormInput', () => {
  it('offers ISO, DIN, CSN and EN', () => {
    const wrapper = mountInput(null, null)
    expect(wrapper.find('[data-test="norm-type"]').text()).toBe('ISO,DIN,CSN,EN')
  })

  it('disables the code until a type is picked', () => {
    expect(
      mountInput(null, null).find('[data-test="norm-code"]').attributes('disabled'),
    ).toBeDefined()
    expect(
      mountInput('EN', '10025').find('[data-test="norm-code"]').attributes('disabled'),
    ).toBeUndefined()
  })

  it('emits the typed code', async () => {
    const wrapper = mountInput('DIN', '')
    await wrapper.find('[data-test="norm-code"]').setValue('84')
    expect(wrapper.emitted('update:code')?.[0]).toEqual(['84'])
  })
})
