import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import TemplateEditor from '../TemplateEditor.vue'

const mountEditor = (modelValue = '<p>{{ order.code }}</p>') => {
  const wrapper = mount(TemplateEditor, {
    props: {
      modelValue,
      'onUpdate:modelValue': (value: string) => wrapper.setProps({ modelValue: value }),
    },
    attachTo: document.body,
  })
  return wrapper
}

const editorText = (wrapper: ReturnType<typeof mountEditor>) => wrapper.find('.cm-content').text()

describe('TemplateEditor', () => {
  it('shows the model value', () => {
    const wrapper = mountEditor()

    expect(editorText(wrapper)).toContain('{{ order.code }}')
    wrapper.unmount()
  })

  it('follows external model changes (another template loaded)', async () => {
    const wrapper = mountEditor()

    await wrapper.setProps({ modelValue: '<h1>other</h1>' })
    await nextTick()

    expect(editorText(wrapper)).toContain('other')
    expect(editorText(wrapper)).not.toContain('order.code')
    wrapper.unmount()
  })

  it('inserts a snippet at the cursor and reports the change through v-model', async () => {
    const wrapper = mountEditor('ab')

    ;(wrapper.vm as unknown as { insert: (text: string) => void }).insert('{{ x }}')
    await nextTick()

    expect(wrapper.props('modelValue')).toBe('{{ x }}ab')
    wrapper.unmount()
  })
})
