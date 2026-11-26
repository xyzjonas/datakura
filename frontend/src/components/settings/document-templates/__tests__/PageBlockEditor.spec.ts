import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { PageSchema } from '@/client'
import PageBlockEditor from '../PageBlockEditor.vue'

const mountEditor = (page: Required<PageSchema>) =>
  mount(PageBlockEditor, {
    props: { modelValue: page },
    global: {
      stubs: {
        LayoutBlock: { template: '<div><slot /></div>' },
        QInput: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
      },
    },
  })

const page = (): Required<PageSchema> => ({
  margin_top: 60,
  margin_right: 53,
  margin_bottom: 60,
  margin_left: 53,
})

describe('PageBlockEditor', () => {
  it.each([
    ['0', 0],
    ['25', 25],
    ['-5', 0],
    ['999', 200],
    ['', 0],
    ['abc', 0],
  ])('margin input "%s" -> %s px', async (input, expected) => {
    const wrapper = mountEditor(page())

    await wrapper.find('[data-test="margin_left"]').setValue(input)

    expect((wrapper.props('modelValue') as Required<PageSchema>).margin_left).toBe(expected)
  })

  it('edits each side independently', async () => {
    const wrapper = mountEditor(page())

    await wrapper.find('[data-test="margin_top"]').setValue('1')
    await wrapper.find('[data-test="margin_bottom"]').setValue('2')

    expect(wrapper.props('modelValue')).toEqual({
      margin_top: 1,
      margin_right: 53,
      margin_bottom: 2,
      margin_left: 53,
    })
  })
})
