import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { LogoBlockSchema } from '@/client'
import LogoBlockEditor from '../LogoBlockEditor.vue'

const mountEditor = (modelValue: Required<LogoBlockSchema>) =>
  mount(LogoBlockEditor, {
    props: { modelValue },
    global: {
      stubs: {
        LayoutBlock: { template: '<div><slot /></div>' },
        QFile: true,
        QBtnToggle: true,
        QBtn: {
          emits: ['click'],
          template: '<button @click="$emit(\'click\')" />',
        },
      },
    },
  })

describe('LogoBlockEditor', () => {
  it('shows no preview or remove button without an image', () => {
    const wrapper = mountEditor({ enabled: false, image: null, align: 'left' })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('[data-test="logo-remove"]').exists()).toBe(false)
  })

  it('removes the image and switches the logo off', async () => {
    const logo = { enabled: true, image: 'data:image/png;base64,AAAA', align: 'center' as const }
    const wrapper = mountEditor(logo)
    expect(wrapper.find('img').attributes('src')).toBe(logo.image)

    await wrapper.find('[data-test="logo-remove"]').trigger('click')

    expect(logo.image).toBeNull()
    expect(logo.enabled).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
  })
})
