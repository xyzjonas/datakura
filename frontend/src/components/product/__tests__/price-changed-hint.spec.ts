import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PriceChangedHint from '../PriceChangedHint.vue'

installQuasarPlugin()

describe('PriceChangedHint', () => {
  it('renders the change date', () => {
    const wrapper = mount(PriceChangedHint, { props: { date: '2026-11-17T10:00:00Z' } })
    expect(wrapper.text()).toContain('změněno 17. 11. 2026')
  })

  it.each([undefined, null, ''])('renders nothing for %s', (date) => {
    const wrapper = mount(PriceChangedHint, { props: { date } })
    expect(wrapper.text()).toBe('')
  })
})
