import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { CatalogFieldSchema, LayoutFieldSchema } from '@/client'
import FieldListEditor from '../FieldListEditor.vue'

const OPTIONS: CatalogFieldSchema[] = [
  { key: 'name', label: 'Název' },
  { key: 'address', label: 'Adresa' },
  { key: 'phone', label: 'Telefon' },
]

const mountEditor = (modelValue: LayoutFieldSchema[]) => {
  const wrapper = mount(FieldListEditor, {
    props: {
      modelValue,
      options: OPTIONS,
      'onUpdate:modelValue': (value: LayoutFieldSchema[]) =>
        wrapper.setProps({ modelValue: value }),
    },
    global: {
      stubs: {
        QBtn: {
          props: ['disable'],
          emits: ['click'],
          template: '<button :disabled="disable" @click="$emit(\'click\')" />',
        },
        QInput: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        QSelect: {
          props: ['options'],
          emits: ['update:modelValue'],
          template:
            '<div><button v-for="o in options" :key="o.key" class="option" @click="$emit(\'update:modelValue\', o)">{{ o.key }}</button></div>',
        },
      },
    },
  })
  return wrapper
}

const keys = (wrapper: ReturnType<typeof mountEditor>) =>
  (wrapper.props('modelValue') as LayoutFieldSchema[]).map((f) => f.key)

describe('FieldListEditor', () => {
  it('only offers the attributes that are not picked yet', () => {
    const wrapper = mountEditor([{ key: 'name', label: 'Název' }])

    expect(wrapper.findAll('.option').map((o) => o.text())).toEqual(['address', 'phone'])
  })

  it('adds an attribute with its default caption to the end', async () => {
    const wrapper = mountEditor([{ key: 'name', label: 'Název' }])

    await wrapper.findAll('.option')[0]!.trigger('click')

    expect(wrapper.props('modelValue')).toEqual([
      { key: 'name', label: 'Název' },
      { key: 'address', label: 'Adresa' },
    ])
    expect(wrapper.findAll('.option').map((o) => o.text())).toEqual(['phone'])
  })

  it('hides the picker when everything is picked', () => {
    const wrapper = mountEditor(OPTIONS.map((o) => ({ ...o })))

    expect(wrapper.find('[data-test="add-field"]').exists()).toBe(false)
  })

  it('removes an attribute', async () => {
    const wrapper = mountEditor(OPTIONS.map((o) => ({ ...o })))

    await wrapper.findAll('[data-test="remove"]')[1]!.trigger('click')

    expect(keys(wrapper)).toEqual(['name', 'phone'])
  })

  it('reorders attributes and disables the moves past the ends', async () => {
    const wrapper = mountEditor(OPTIONS.map((o) => ({ ...o })))
    const up = () => wrapper.findAll('[data-test="move-up"]')
    const down = () => wrapper.findAll('[data-test="move-down"]')

    expect(up()[0]!.attributes('disabled')).toBeDefined()
    expect(down()[2]!.attributes('disabled')).toBeDefined()

    await down()[0]!.trigger('click')
    expect(keys(wrapper)).toEqual(['address', 'name', 'phone'])
    await up()[2]!.trigger('click')
    expect(keys(wrapper)).toEqual(['address', 'phone', 'name'])
  })

  it('edits the caption, an empty one means no caption', async () => {
    const wrapper = mountEditor([{ key: 'name', label: 'Název' }])

    await wrapper.find('[data-test="field-label"]').setValue('')

    expect(wrapper.props('modelValue')).toEqual([{ key: 'name', label: '' }])
  })
})
