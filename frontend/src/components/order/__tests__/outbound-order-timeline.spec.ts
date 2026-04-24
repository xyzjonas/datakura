import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import OutboundOrderTimeline from '../OutboundOrderTimeline.vue'

installQuasarPlugin()

describe('OutboundOrderTimeline', () => {
  it('does not render packing or shipping steps', () => {
    const wrapper = mount(OutboundOrderTimeline, {
      props: { state: 'sent' },
      global: {
        stubs: {
          QStepper: { template: '<div><slot /></div>' },
          QStep: {
            props: ['title', 'caption'],
            template: '<div><span>{{ title }}</span><span>{{ caption }}</span></div>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Kompletace')
    expect(wrapper.text()).toContain('Odesláno')
    expect(wrapper.text()).not.toContain('Balení')
    expect(wrapper.text()).not.toContain('Expedice')
  })
})
