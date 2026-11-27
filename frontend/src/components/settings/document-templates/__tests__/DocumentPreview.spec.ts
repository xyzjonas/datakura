import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DocumentPreview from '../DocumentPreview.vue'

const mountPreview = (props: InstanceType<typeof DocumentPreview>['$props']) =>
  mount(DocumentPreview, { props, global: { stubs: { QInnerLoading: true } } })

describe('DocumentPreview', () => {
  it('renders the html in a script-less sandboxed iframe', () => {
    const frame = mountPreview({ html: '<p>hello</p>' }).find('iframe')

    expect(frame.attributes('srcdoc')).toBe('<p>hello</p>')
    expect(frame.attributes('sandbox')).toBe('allow-same-origin')
  })

  it('asks for a record while there is nothing to show', () => {
    const wrapper = mountPreview({ html: '' })

    expect(wrapper.find('iframe').exists()).toBe(false)
    expect(wrapper.text()).toContain('Vyberte záznam')
  })

  it('reports a failed render', () => {
    const wrapper = mountPreview({ html: '', failed: true })

    expect(wrapper.text()).toContain('Náhled se nepodařilo načíst')
  })

  it('keeps the last page while loading', () => {
    const wrapper = mountPreview({ html: '<p>x</p>', loading: true })

    expect(wrapper.find('iframe').exists()).toBe(true)
  })
})
