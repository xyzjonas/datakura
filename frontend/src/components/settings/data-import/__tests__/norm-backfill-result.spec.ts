import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { NormBackfillResultSchema } from '@/client'
import NormBackfillResult from '../NormBackfillResult.vue'

const stubs = {
  QBanner: { template: '<div><slot /></div>' },
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}

const result = (overrides: Partial<NormBackfillResultSchema> = {}): NormBackfillResultSchema => ({
  products_scanned: 10,
  customs_filled: 8,
  norms_linked: 7,
  norms_created: 5,
  aliases_linked: 3,
  norms_kept: 0,
  without_customs: 2,
  without_norm: 3,
  invalid_count: 0,
  invalid: [],
  ...overrides,
})

const mountWith = (value: NormBackfillResultSchema) =>
  mount(NormBackfillResult, { props: { result: value }, global: { stubs } })

describe('NormBackfillResult', () => {
  it('reports converted products and what is still missing', () => {
    const wrapper = mountWith(result())

    const summary = wrapper.find('[data-test="norm-result-summary"]').text()
    expect(summary).toContain('Zpracováno produktů 10')
    expect(summary).toContain('normu získalo 7')
    expect(summary).toContain('celní nomenklaturu 8')
    expect(wrapper.find('[data-test="norm-result-missing"]').text()).toContain(
      'Stále bez normy: 3, bez celní nomenklatury: 2',
    )
    expect(wrapper.find('[data-test="norm-result-invalid"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="norm-result-kept"]').exists()).toBe(false)
  })

  it('lists the flagged invalid values', () => {
    const wrapper = mountWith(
      result({
        invalid_count: 1,
        invalid: [{ product_code: 'P-1', key: 'NORM', value: 'GOST 1', reason: 'no known norm' }],
      }),
    )

    const invalid = wrapper.find('[data-test="norm-result-invalid"]').text()
    expect(invalid).toContain('Neplatné hodnoty (1)')
    expect(invalid).toContain('P-1')
    expect(invalid).toContain('GOST 1')
    expect(invalid).not.toContain('zobrazeno prvních')
  })

  it('tells when the list of invalid values is capped', () => {
    const wrapper = mountWith(
      result({
        invalid_count: 900,
        invalid: [{ product_code: 'P-1', key: 'k', value: 'v', reason: 'r' }],
      }),
    )

    expect(wrapper.find('[data-test="norm-result-invalid"]').text()).toContain(
      'zobrazeno prvních 1',
    )
  })

  it('mentions products whose norm was kept', () => {
    const wrapper = mountWith(result({ norms_kept: 4 }))

    expect(wrapper.find('[data-test="norm-result-kept"]').text()).toContain('4')
  })
})
