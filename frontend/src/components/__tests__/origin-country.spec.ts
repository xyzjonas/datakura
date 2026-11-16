import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CountryBadge from '../CountryBadge.vue'
import OriginCountryMarker from '../OriginCountryMarker.vue'
import BulkOriginCountryButton from '../order/BulkOriginCountryButton.vue'
import CountrySelect from '../selects/CountrySelect.vue'

installQuasarPlugin()

describe('CountryBadge', () => {
  it('shows flag and localized name', () => {
    const text = mount(CountryBadge, { props: { code: 'DE' } }).text()
    expect(text).toContain('🇩🇪')
    expect(text).toContain('Německo')
  })

  it.each([null, undefined, ''])('renders nothing for %s', (code) => {
    expect(
      mount(CountryBadge, { props: { code } }).find('[data-test="country-badge"]').exists(),
    ).toBe(false)
  })
})

describe('OriginCountryMarker', () => {
  it('prefers the country over the warning', () => {
    const wrapper = mount(OriginCountryMarker, { props: { country: 'CZ', missing: true } })
    expect(wrapper.find('[data-test="country-badge"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="missing-origin-country"]').exists()).toBe(false)
  })

  it('warns when the country is required but missing', () => {
    const wrapper = mount(OriginCountryMarker, { props: { country: null, missing: true } })
    expect(wrapper.get('[data-test="missing-origin-country"]').text()).toContain(
      'chybí země původu',
    )
  })

  it('renders nothing when nothing is required', () => {
    const wrapper = mount(OriginCountryMarker, { props: { country: null } })
    expect(wrapper.find('[data-test="country-badge"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="missing-origin-country"]').exists()).toBe(false)
  })
})

describe('BulkOriginCountryButton', () => {
  const stubs = {
    QDialog: { template: '<div><slot /></div>' },
    QCard: { template: '<div><slot /></div>' },
    QCardSection: { template: '<div><slot /></div>' },
    QCardActions: { template: '<div><slot /></div>' },
    CountrySelect: true,
  }

  const mountIt = (props: Record<string, unknown> = {}) =>
    mount(BulkOriginCountryButton, { props, global: { stubs } })

  it('is disabled on demand', () => {
    expect(
      mountIt({ disabled: true }).get('[data-test="bulk-origin-country"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('cannot apply without a chosen country', () => {
    expect(
      mountIt().get('[data-test="bulk-origin-country-apply"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('emits the chosen country', async () => {
    const wrapper = mountIt()
    wrapper.findComponent(CountrySelect).vm.$emit('update:modelValue', 'VN')
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="bulk-origin-country-apply"]').trigger('click')

    expect(wrapper.emitted('apply')).toEqual([['VN']])
  })

  it('emits null to clear all items', async () => {
    const wrapper = mountIt()

    await wrapper.get('[data-test="bulk-origin-country-clear"]').trigger('click')

    expect(wrapper.emitted('apply')).toEqual([[null]])
  })
})

describe('CountrySelect', () => {
  const mountSelect = (modelValue: string | null = null) =>
    mount(CountrySelect, { props: { modelValue } })

  it('shows the flag of the selected country', () => {
    expect(mountSelect('DE').text()).toContain('🇩🇪')
  })

  it('shows a neutral icon without a selection', () => {
    expect(mountSelect(null).text()).not.toContain('🇩🇪')
  })

  it.each([
    ['VN', 'VN'],
    [null, null],
    [undefined, null],
  ])('selecting %s updates the model to %s', (selected, expected) => {
    const wrapper = mountSelect('DE')

    wrapper.getComponent({ name: 'QSelect' }).vm.$emit('update:modelValue', selected)

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([expected])
  })
})
