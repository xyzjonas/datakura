import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { provideRequiresOriginCountry } from '@/composables/use-outbound-document-api'
import { defineComponent, h } from 'vue'
import OutboundItemRequirementBadges from '../OutboundItemRequirementBadges.vue'

installQuasarPlugin()

const mountIt = (props: Record<string, unknown>, requiresCountry = false) =>
  mount(
    defineComponent({
      setup() {
        provideRequiresOriginCountry(requiresCountry)
        return () => h(OutboundItemRequirementBadges, props)
      },
    }),
  )

describe('OutboundItemRequirementBadges', () => {
  it('renders nothing without any requirement', () => {
    expect(mountIt({}).find('[data-test="requirement-badges"]').exists()).toBe(false)
  })

  it('shows every specified requirement at once', () => {
    const wrapper = mountIt({
      packageType: 'B0100',
      batchCode: 'BAT-1',
      originCountry: 'DE',
    })

    const text = wrapper.text()
    expect(text).toContain('B0100')
    expect(text).toContain('BAT-1')
    expect(text).toContain('Německo')
  })

  it.each([
    [{ packageType: 'B0100' }, 'B0100'],
    [{ batchCode: 'BAT-1' }, 'BAT-1'],
    [{ originCountry: 'CZ' }, 'Česko'],
  ])('shows a lone requirement %o', (props, expected) => {
    expect(mountIt(props).text()).toContain(expected)
  })

  it('warns about a missing country only for customers requiring it', () => {
    expect(mountIt({}, true).find('[data-test="missing-origin-country"]').exists()).toBe(true)
    expect(
      mountIt({ packageType: 'B0100' }).find('[data-test="missing-origin-country"]').exists(),
    ).toBe(false)
  })

  it('keeps the other badges next to the missing-country warning', () => {
    const wrapper = mountIt({ batchCode: 'BAT-1' }, true)
    expect(wrapper.text()).toContain('BAT-1')
    expect(wrapper.find('[data-test="missing-origin-country"]').exists()).toBe(true)
  })
})
