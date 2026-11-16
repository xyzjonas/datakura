import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CustomerProductCodeInput from '../CustomerProductCodeInput.vue'

installQuasarPlugin()

const mountInput = (props: Record<string, unknown>) => mount(CustomerProductCodeInput, { props })

describe('CustomerProductCodeInput', () => {
  it.each([
    [{ required: true, modelValue: null }, true],
    [{ required: true, modelValue: '' }, true],
    [{ required: true, modelValue: 'A-1' }, false],
    [{ required: false, modelValue: null }, false],
    [{ modelValue: null }, false],
  ])('error state for %j is %s', (props, error) => {
    const wrapper = mountInput(props)
    expect(wrapper.find('.q-field--error').exists()).toBe(error)
  })
})
