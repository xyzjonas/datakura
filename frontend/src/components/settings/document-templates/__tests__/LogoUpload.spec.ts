import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import LogoUpload from '../LogoUpload.vue'

const mountUpload = (modelValue: string | null) =>
  mount(LogoUpload, {
    props: { modelValue },
    global: {
      stubs: {
        QFile: true,
        QBtn: {
          emits: ['click'],
          template: '<button @click="$emit(\'click\')" />',
        },
      },
    },
  })

describe('LogoUpload', () => {
  it('shows no preview or remove button without an image', () => {
    const wrapper = mountUpload(null)

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('[data-test="logo-remove"]').exists()).toBe(false)
  })

  it('previews the image and removes it', async () => {
    const image = 'data:image/png;base64,AAAA'
    const wrapper = mountUpload(image)
    expect(wrapper.find('img').attributes('src')).toBe(image)

    await wrapper.find('[data-test="logo-remove"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([[null]])
  })
})
