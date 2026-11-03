import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { BatchSchema } from '@/client'
import ItemBatch from '../ItemBatch.vue'

installQuasarPlugin()

const batch = (overrides: Record<string, unknown> = {}) =>
  ({
    id: 5,
    primary_barcode: { code: 'BAT-1' },
    certification: null,
    ...overrides,
  }) as unknown as BatchSchema

const mountIt = (b?: BatchSchema | null) =>
  mount(ItemBatch, {
    props: { batch: b },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })

describe('ItemBatch', () => {
  it('shows a dash for items without a batch', () => {
    const wrapper = mountIt(null)
    expect(wrapper.text()).toBe('-')
    expect(wrapper.find('[data-test="certification-badge"]').exists()).toBe(false)
  })

  it('shows the batch code without a certification badge for plain batches', () => {
    const wrapper = mountIt(batch())
    expect(wrapper.text()).toContain('BAT-1')
    expect(wrapper.find('[data-test="certification-badge"]').exists()).toBe(false)
  })

  it('falls back to the batch id when the batch has no barcode', () => {
    expect(mountIt(batch({ primary_barcode: null })).text()).toContain('#5')
  })

  it('shows a linked certification badge for certified batches', () => {
    const wrapper = mountIt(batch({ certification: { id: 9, code: 'ISO-9001' } }))
    expect(wrapper.text()).toContain('BAT-1')
    expect(wrapper.get('[data-test="certification-badge-link"]').text()).toContain('ISO-9001')
  })
})
