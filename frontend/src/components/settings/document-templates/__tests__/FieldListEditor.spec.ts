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
        QTooltip: true,
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

const value = (wrapper: ReturnType<typeof mountEditor>) =>
  wrapper.props('modelValue') as LayoutFieldSchema[]
const keys = (wrapper: ReturnType<typeof mountEditor>) => value(wrapper).map((f) => f.key)
const name = (): LayoutFieldSchema => ({ key: 'name', label: 'Název' })

describe('FieldListEditor', () => {
  it('adds an attribute with its default caption to the end, even when already picked', async () => {
    const wrapper = mountEditor([name()])

    await wrapper.findAll('.option')[0]!.trigger('click')

    expect(value(wrapper)).toEqual([name(), name()])
  })

  it('adds a static text without a caption', async () => {
    const wrapper = mountEditor([])

    await wrapper.find('[data-test="add-static"]').trigger('click')

    expect(value(wrapper)).toEqual([{ text: 'text', show_label: false }])
    expect(wrapper.find('[data-test="static-text"]').exists()).toBe(true)
  })

  it('edits the static text', async () => {
    const wrapper = mountEditor([{ text: 'old', show_label: false }])

    await wrapper.find('[data-test="static-text"]').setValue('Díky')

    expect(value(wrapper)[0]!.text).toBe('Díky')
  })

  it('adds a composite chaining the first attributes, captions hidden by default', async () => {
    const wrapper = mountEditor([])

    await wrapper.find('[data-test="add-composite"]').trigger('click')

    expect(value(wrapper)).toEqual([
      {
        show_label: false,
        direction: 'row',
        separator: ', ',
        parts: [
          { key: 'name', label: 'Název', show_label: false },
          { key: 'address', label: 'Adresa', show_label: false },
        ],
      },
    ])
    expect(wrapper.findAll('[data-test="part"]')).toHaveLength(2)
  })

  it('gives composite parts the same options as a single attribute', async () => {
    const wrapper = mountEditor([
      { parts: [{ key: 'name', show_label: false }], show_label: false },
    ])
    const part = wrapper.find('[data-test="part"]')

    for (const toggle of ['toggle-label', 'toggle-bold', 'toggle-muted', 'toggle-barcode']) {
      expect(part.find(`[data-test="${toggle}"]`).exists()).toBe(true)
    }
    expect(part.find('[data-test="font-size"]').exists()).toBe(true)
    await part.find('[data-test="toggle-bold"]').trigger('click')
    await part.find('[data-test="toggle-barcode"]').trigger('click')

    const edited = value(wrapper)[0]!.parts![0]!
    expect(edited).toMatchObject({ bold: true, barcode: true })
  })

  it('has no barcode option on the composite itself, the parts have it', () => {
    const wrapper = mountEditor([{ parts: [{ key: 'name' }] }])
    const composite = wrapper.find('[data-test="field"]')

    // the first toolbar belongs to the composite, the second one to its part
    const toolbars = composite.findAll('[data-test="toggle-bold"]')
    expect(toolbars).toHaveLength(2)
    expect(composite.findAll('[data-test="toggle-barcode"]')).toHaveLength(1)
  })

  it('keeps an emptied composite editable', async () => {
    const wrapper = mountEditor([{ parts: [{ key: 'name' }] }])

    await wrapper.find('[data-test="part"] [data-test="remove"]').trigger('click')

    expect(wrapper.find('[data-test="add-static"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-test="part"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-test="field"]')).toHaveLength(1)
  })

  it('reorders and removes parts of a composite', async () => {
    const wrapper = mountEditor([
      { parts: [{ key: 'name' }, { key: 'address' }, { key: 'phone' }] },
    ])
    const partKeys = () => value(wrapper)[0]!.parts!.map((p) => p.key)

    await wrapper.findAll('[data-test="part"] [data-test="move-down"]')[0]!.trigger('click')
    expect(partKeys()).toEqual(['address', 'name', 'phone'])
    await wrapper.findAll('[data-test="part"] [data-test="remove"]')[2]!.trigger('click')
    expect(partKeys()).toEqual(['address', 'name'])
  })

  it('toggles the direction of a composite and hides the separator in column mode', async () => {
    const wrapper = mountEditor([{ parts: [{ key: 'name' }], direction: 'row', separator: ', ' }])
    expect(wrapper.find('[data-test="separator"]').exists()).toBe(true)

    await wrapper.find('[data-test="toggle-direction"]').trigger('click')

    expect(value(wrapper)[0]!.direction).toBe('column')
    expect(wrapper.find('[data-test="separator"]').exists()).toBe(false)
  })

  it('removes an attribute', async () => {
    const wrapper = mountEditor([
      name(),
      { key: 'address', label: 'Adresa' },
      { key: 'phone', label: 'Telefon' },
    ])

    await wrapper.findAll('[data-test="field"] > [data-test="remove"]')[1]!.trigger('click')

    expect(keys(wrapper)).toEqual(['name', 'phone'])
  })

  it('reorders attributes and disables the moves past the ends', async () => {
    const wrapper = mountEditor([
      name(),
      { key: 'address', label: 'Adresa' },
      { key: 'phone', label: 'Telefon' },
    ])
    const up = () => wrapper.findAll('[data-test="field"] > div > [data-test="move-up"]')
    const down = () => wrapper.findAll('[data-test="field"] > div > [data-test="move-down"]')

    expect(up()[0]!.attributes('disabled')).toBeDefined()
    expect(down()[2]!.attributes('disabled')).toBeDefined()

    await down()[0]!.trigger('click')
    expect(keys(wrapper)).toEqual(['address', 'name', 'phone'])
    await up()[2]!.trigger('click')
    expect(keys(wrapper)).toEqual(['address', 'phone', 'name'])
  })

  it('edits the caption, an empty one means no caption', async () => {
    const wrapper = mountEditor([name()])

    await wrapper.find('[data-test="field-label"]').setValue('')

    expect(value(wrapper)).toEqual([{ key: 'name', label: '' }])
  })

  it('toggles the caption visibility without losing the caption', async () => {
    const wrapper = mountEditor([name()])

    await wrapper.find('[data-test="toggle-label"]').trigger('click')
    expect(value(wrapper)).toEqual([{ key: 'name', label: 'Název', show_label: false }])

    await wrapper.find('[data-test="toggle-label"]').trigger('click')
    expect(value(wrapper)).toEqual([{ key: 'name', label: 'Název', show_label: true }])
  })

  it.each(['bold', 'muted', 'barcode'] as const)('toggles %s', async (option) => {
    const wrapper = mountEditor([name()])

    await wrapper.find(`[data-test="toggle-${option}"]`).trigger('click')
    expect(value(wrapper)[0]![option]).toBe(true)

    await wrapper.find(`[data-test="toggle-${option}"]`).trigger('click')
    expect(value(wrapper)[0]![option]).toBe(false)
  })

  it('offers the text under the barcode only when the barcode is on', async () => {
    const wrapper = mountEditor([name()])
    expect(wrapper.find('[data-test="toggle-barcode-text"]').exists()).toBe(false)

    await wrapper.find('[data-test="toggle-barcode"]').trigger('click')
    await wrapper.find('[data-test="toggle-barcode-text"]').trigger('click')

    expect(value(wrapper)[0]).toMatchObject({ barcode: true, barcode_text: true })
  })

  it.each([
    ['14', 14],
    ['', null],
    ['abc', null],
    ['0', null],
  ])('font size input "%s" -> %s', async (input, expected) => {
    const wrapper = mountEditor([name()])

    await wrapper.find('[data-test="font-size"]').setValue(input)

    expect(value(wrapper)[0]!.font_size).toBe(expected)
  })
})
