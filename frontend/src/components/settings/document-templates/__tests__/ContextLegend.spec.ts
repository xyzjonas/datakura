import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { DocumentLegendSchema } from '@/client'
import ContextLegend from '../ContextLegend.vue'

const legend: DocumentLegendSchema = {
  fields: [
    { path: 'order.code', type: 'text' },
    { path: 'order.items', type: 'list' },
    { path: 'order.items[].product.name', type: 'text' },
  ],
  filters: [
    { name: 'date', signature: 'date(fmt)', description: 'Formats a date' },
    { name: 'money', signature: 'money(currency)', description: 'Amount with currency' },
  ],
}

const mountLegend = (props: { legend?: DocumentLegendSchema } = { legend }) =>
  mount(ContextLegend, {
    props,
    global: {
      stubs: {
        QInput: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        QIcon: true,
      },
    },
  })

const buttons = (wrapper: ReturnType<typeof mountLegend>) => wrapper.findAll('button')

describe('ContextLegend', () => {
  it('lists all fields and filters', () => {
    const texts = buttons(mountLegend()).map((b) => b.text())

    expect(texts).toHaveLength(5)
    expect(texts[0]).toContain('order.code')
    expect(texts[3]).toContain('date(fmt)')
  })

  it('inserts a snippet of the clicked field', async () => {
    const wrapper = mountLegend()

    await buttons(wrapper)[0]!.trigger('click')
    await buttons(wrapper)[2]!.trigger('click')

    expect(wrapper.emitted('insert')).toEqual([['{{ order.code }}'], ['{{ item.product.name }}']])
  })

  it('inserts a filter after a pipe', async () => {
    const wrapper = mountLegend()

    await buttons(wrapper)[4]!.trigger('click')

    expect(wrapper.emitted('insert')).toEqual([['|money']])
  })

  it.each([
    ['PRODUCT', 1, 0],
    ['date', 0, 1],
    ['nothing-like-this', 0, 0],
  ])('search %j narrows fields/filters', async (term, fields, filters) => {
    const wrapper = mountLegend()

    await wrapper.find('input').setValue(term)

    expect(buttons(wrapper)).toHaveLength(fields + filters)
    if (!fields && !filters) expect(wrapper.text()).toContain('Nic nenalezeno')
  })

  it('renders without a legend', () => {
    expect(buttons(mountLegend({}))).toHaveLength(0)
  })
})
