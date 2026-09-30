import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { DataImportJobStatusSchema } from '@/client'
import DataImportProgress from '../DataImportProgress.vue'

const stubs = {
  QCard: { template: '<div><slot /></div>' },
  QBtn: {
    props: ['label'],
    emits: ['click'],
    template: '<button :data-test="$attrs[\'data-test\']" @click="$emit(\'click\')">{{ label }}</button>',
  },
  QSpace: true,
  QLinearProgress: {
    props: ['value', 'indeterminate'],
    template:
      '<div data-test="bar" :data-value="value" :data-indeterminate="indeterminate !== undefined ? \'yes\' : undefined" />',
  },
  QBanner: { template: '<div><slot /></div>' },
}

const mountWith = (status: DataImportJobStatusSchema) =>
  mount(DataImportProgress, { props: { status }, global: { stubs } })

describe('DataImportProgress', () => {
  it('shows percentage, stage, phase and remaining records while running', () => {
    const wrapper = mountWith({
      job_id: 'j',
      state: 'running',
      stage: 'products',
      phase: 'importing',
      stage_done: 150,
      stage_total: 1000,
      percent: 12.5,
    })

    const label = wrapper.find('[data-test="progress-label"]').text()
    expect(label).toContain('12.5 %')
    expect(label).toContain('products - ukládání')
    expect(label).toContain('zbývá 850 z 1000 záznamů')
    expect(wrapper.find('[data-test="bar"]').attributes('data-value')).toBe('0.125')
  })

  it.each([
    ['over-reported counts never show negative remaining', 12, 10, 'zbývá 0 z 10'],
    ['unknown phase is shown as is', 0, 10, 'zbývá 10 z 10'],
  ])('%s', (_label, done, total, expected) => {
    const wrapper = mountWith({
      job_id: 'j',
      state: 'running',
      stage: 's',
      phase: 'custom',
      stage_done: done,
      stage_total: total,
      percent: 1,
    })

    expect(wrapper.text()).toContain(expected)
  })

  it('hides record counts while the total is unknown (parsing / validating)', () => {
    const wrapper = mountWith({
      job_id: 'j',
      state: 'running',
      stage: 'products',
      phase: 'parsing',
      stage_done: 0,
      stage_total: 0,
      percent: 0,
    })

    expect(wrapper.text()).toContain('načítání souboru')
    expect(wrapper.text()).not.toContain('zbývá')
  })

  it('shows an indeterminate bar and lets the user stop watching a pending job', async () => {
    const wrapper = mountWith({ job_id: 'j', state: 'pending' })

    expect(wrapper.find('[data-test="bar"]').attributes('data-indeterminate')).toBeDefined()
    await wrapper.find('[data-test="stop-watching"]').trigger('click')
    expect(wrapper.emitted('stop')).toHaveLength(1)
  })

  it('shows the error of a failed import', () => {
    const wrapper = mountWith({ job_id: 'j', state: 'failed', error: 'products: Record #1' })

    expect(wrapper.find('[data-test="progress-error"]').text()).toContain('products: Record #1')
    expect(wrapper.find('[data-test="stop-watching"]').exists()).toBe(false)
  })
})
