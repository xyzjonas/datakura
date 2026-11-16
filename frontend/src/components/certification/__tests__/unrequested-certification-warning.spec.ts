import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import UnrequestedCertificationWarning from '../UnrequestedCertificationWarning.vue'

installQuasarPlugin()

describe('UnrequestedCertificationWarning', () => {
  it('names the certification and starts unconfirmed', () => {
    const wrapper = mount(UnrequestedCertificationWarning, {
      props: { code: 'ISO-9001', modelValue: false },
    })

    expect(wrapper.text()).toContain('ISO-9001')
    expect(wrapper.text()).toContain('nepožaduje')
  })

  it('confirms through the checkbox', async () => {
    const wrapper = mount(UnrequestedCertificationWarning, {
      props: {
        modelValue: false,
        'onUpdate:modelValue': (v: boolean) => wrapper.setProps({ modelValue: v }),
      },
    })

    await wrapper.get('[data-test="confirm-unrequested-certification"]').trigger('click')

    expect(wrapper.props('modelValue')).toBe(true)
  })
})
