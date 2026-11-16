import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CustomerMinimumValueFields from '../CustomerMinimumValueFields.vue'
import ToggleRow from '../ToggleRow.vue'

installQuasarPlugin()

describe('ToggleRow', () => {
  const mountIt = (modelValue = false) =>
    mount(ToggleRow, {
      props: { label: 'Dodavatel', description: 'Dlouhé vysvětlení', modelValue },
    })

  it('renders label and verbose description', () => {
    const text = mountIt().text()
    expect(text).toContain('Dodavatel')
    expect(text).toContain('Dlouhé vysvětlení')
  })

  it.each([true, false])('toggling from %s emits the opposite value', (initial) => {
    const wrapper = mountIt(initial)

    wrapper.getComponent({ name: 'QToggle' }).vm.$emit('update:modelValue', !initial)

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([!initial])
  })
})

describe('CustomerMinimumValueFields', () => {
  it('explains the rounding and can be disabled', () => {
    const wrapper = mount(CustomerMinimumValueFields, { props: { disable: true } })
    expect(wrapper.text()).toContain('Minimální hodnota položky')
    expect(wrapper.getComponent({ name: 'QInput' }).props('disable')).toBe(true)
  })
})
