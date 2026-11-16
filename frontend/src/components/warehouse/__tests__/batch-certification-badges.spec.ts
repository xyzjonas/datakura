import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BatchCertificationBadges from '../BatchCertificationBadges.vue'

installQuasarPlugin()

const mountIt = (props: Record<string, unknown>) =>
  mount(BatchCertificationBadges, {
    props,
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })

describe('BatchCertificationBadges', () => {
  it('shows the batch together with its certification', () => {
    const wrapper = mountIt({ batchCode: 'B-1', certification: { id: 3, code: 'ISO-9001' } })

    expect(wrapper.text()).toContain('B-1')
    expect(wrapper.text()).toContain('ISO-9001')
  })

  it.each([[null], [undefined]])('shows just the batch without certification (%s)', (cert) => {
    const wrapper = mountIt({ batchCode: 'B-1', certification: cert })

    expect(wrapper.text()).toContain('B-1')
    expect(wrapper.find('[data-test="certification-badge"]').exists()).toBe(false)
  })
})
