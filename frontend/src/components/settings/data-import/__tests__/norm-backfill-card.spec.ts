import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref, type Ref } from 'vue'

import NormBackfillCard from '../NormBackfillCard.vue'

const mocks = vi.hoisted(() => ({
  start: vi.fn(),
  dismiss: vi.fn(),
  status: null as unknown as Ref<unknown>,
  running: null as unknown as Ref<boolean>,
}))

vi.mock('@/composables/use-norm-backfill-job', () => ({
  useNormBackfillJob: () => mocks,
}))

const stubs = {
  QBtn: {
    props: ['label', 'disable', 'loading'],
    emits: ['click'],
    template:
      '<button :data-test="$attrs[\'data-test\']" :disabled="disable" @click="$emit(\'click\')">{{ label }}</button>',
  },
  QCard: { template: '<div><slot /></div>' },
  QBanner: { template: '<div><slot /></div>' },
  QLinearProgress: { props: ['value'], template: '<div data-test="bar" :data-value="value" />' },
  NormBackfillResult: { template: '<div data-test="result-stub" />' },
}

const mountCard = () => mount(NormBackfillCard, { global: { stubs } })

describe('NormBackfillCard', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((m) => typeof m === 'function' && m.mockReset())
    mocks.status = ref(null)
    mocks.running = ref(false)
  })

  it('starts the backfill and shows nothing before a job exists', async () => {
    const wrapper = mountCard()

    expect(wrapper.find('[data-test="norm-progress"]').exists()).toBe(false)
    await wrapper.find('[data-test="norm-backfill-start"]').trigger('click')
    expect(mocks.start).toHaveBeenCalledOnce()
  })

  it('shows the progress while running and disables the button', () => {
    mocks.status.value = {
      job_id: 'j',
      state: 'running',
      percent: 42,
      stage_done: 21,
      stage_total: 50,
    }
    mocks.running.value = true

    const wrapper = mountCard()

    expect(wrapper.find('[data-test="norm-progress"]').text()).toContain('42.0 %')
    expect(wrapper.find('[data-test="norm-progress"]').text()).toContain('21 z 50')
    expect(wrapper.find('[data-test="bar"]').attributes('data-value')).toBe('0.42')
    expect(wrapper.find('[data-test="norm-backfill-start"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-test="norm-backfill-dismiss"]').exists()).toBe(false)
  })

  it('shows the report once the job succeeded and allows to dismiss it', async () => {
    mocks.status.value = {
      job_id: 'j',
      state: 'succeeded',
      percent: 100,
      result: { products_scanned: 1 },
    }

    const wrapper = mountCard()

    expect(wrapper.find('[data-test="result-stub"]').exists()).toBe(true)
    await wrapper.find('[data-test="norm-backfill-dismiss"]').trigger('click')
    expect(mocks.dismiss).toHaveBeenCalledOnce()
  })

  it('shows the error of a failed job', () => {
    mocks.status.value = { job_id: 'j', state: 'failed', error: 'Backfill interrupted: boom' }

    const wrapper = mountCard()

    expect(wrapper.find('[data-test="norm-error"]').text()).toContain('boom')
    expect(wrapper.find('[data-test="result-stub"]').exists()).toBe(false)
  })
})
