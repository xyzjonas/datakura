import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { NormSchema } from '@/client'
import NormLabel from '../NormLabel.vue'

const stubs = {
  QBtn: { template: '<button data-test="norm-aliases-btn"><slot /></button>' },
  QPopupProxy: { template: '<div data-test="popup"><slot /></div>' },
  QCard: { template: '<div><slot /></div>' },
}

const norm = (equivalents: NormSchema['equivalents'] = []): NormSchema => ({
  id: 1,
  code: '84',
  type: 'DIN',
  label: 'DIN 84',
  equivalents,
})

const mountWith = (value?: NormSchema | null) =>
  mount(NormLabel, { props: { norm: value }, global: { stubs } })

describe('NormLabel', () => {
  it.each([null, undefined])('shows a dash for a missing norm (%s)', (value) => {
    const wrapper = mountWith(value)

    expect(wrapper.text()).toBe('-')
    expect(wrapper.find('[data-test="norm-label"]').exists()).toBe(false)
  })

  it('shows the norm without the hint when it has no aliases', () => {
    const wrapper = mountWith(norm())

    expect(wrapper.find('[data-test="norm-label"]').text()).toBe('DIN 84')
    expect(wrapper.find('[data-test="norm-aliases-btn"]').exists()).toBe(false)
  })

  it('lists the aliased norms of other namespaces in the popover', () => {
    const wrapper = mountWith(
      norm([
        { id: 2, code: '1207', type: 'ISO', label: 'ISO 1207' },
        { id: 3, code: '021131', type: 'CSN', label: 'ČSN 021131' },
      ]),
    )

    expect(wrapper.find('[data-test="norm-aliases-btn"]').exists()).toBe(true)
    const items = wrapper.findAll('[data-test="norm-aliases"] li').map((li) => li.text())
    expect(items).toEqual(['ISO 1207', 'ČSN 021131'])
  })
})
