import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TemplatePreview from '../TemplatePreview.vue'

const mountPreview = (props: InstanceType<typeof TemplatePreview>['$props']) =>
  mount(TemplatePreview, {
    props,
    global: {
      stubs: {
        QBanner: { template: '<div class="banner"><slot /></div>' },
        QInnerLoading: true,
      },
    },
  })

describe('TemplatePreview', () => {
  it('renders the html in a script-less sandboxed iframe', () => {
    const wrapper = mountPreview({ html: '<p>hello</p>' })

    const frame = wrapper.find('iframe')
    expect(frame.attributes('srcdoc')).toBe('<p>hello</p>')
    expect(frame.attributes('sandbox')).toBe('allow-same-origin')
    expect(frame.attributes('sandbox')).not.toContain('allow-scripts')
  })

  it('asks for a record while there is nothing to show', () => {
    const wrapper = mountPreview({ html: '' })

    expect(wrapper.find('iframe').exists()).toBe(false)
    expect(wrapper.text()).toContain('Vyberte záznam')
  })

  it('shows the template error with its line, keeping the last good preview', () => {
    const wrapper = mountPreview({
      html: '<p>last good</p>',
      error: { message: 'unexpected end of template', line: 7 },
    })

    expect(wrapper.find('.banner').text()).toContain('Řádek 7')
    expect(wrapper.find('.banner').text()).toContain('unexpected end of template')
    expect(wrapper.find('iframe').attributes('srcdoc')).toBe('<p>last good</p>')
  })

  it('omits the line when the error has none', () => {
    const wrapper = mountPreview({ html: '', error: { message: 'boom', line: null } })

    expect(wrapper.find('.banner').text()).not.toContain('Řádek')
    expect(wrapper.find('.banner').text()).toContain('boom')
  })
})
