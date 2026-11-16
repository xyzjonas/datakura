import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NewOrderItemDialog from '../NewOrderItemDialog.vue'

installQuasarPlugin()

const mountIt = () =>
  mount(NewOrderItemDialog, {
    props: { currency: 'CZK', show: true },
    global: {
      stubs: {
        QDialog: { template: '<div><slot /></div>' },
        QCard: { template: '<div><slot /></div>' },
        QForm: { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
        ProductSearchSelect: true,
        ProductAvailability: true,
        CountrySelect: true,
      },
    },
  })

describe('NewOrderItemDialog - certification', () => {
  it('hides the certificate input until the goods are flagged as certified', async () => {
    const wrapper = mountIt()
    expect(wrapper.find('[data-test="certification-fields"]').exists()).toBe(false)

    await wrapper.get('[data-test="requires-certification"]').trigger('click')

    expect(wrapper.find('[data-test="certification-fields"]').exists()).toBe(true)
  })

  it('emits the flag together with the (still empty) certificate draft', async () => {
    const wrapper = mountIt()
    await wrapper.get('[data-test="requires-certification"]').trigger('click')
    await wrapper.get('form').trigger('submit')

    const [item, keepOpen, draft] = wrapper.emitted('addItem')!.at(-1)!
    expect(item).toMatchObject({ requires_certification: true })
    expect(keepOpen).toBe(false)
    expect(draft).toMatchObject({ mode: 'new', code: '', file: null })
  })

  it('emits no draft for uncertified goods', async () => {
    const wrapper = mountIt()
    await wrapper.get('form').trigger('submit')

    const [item, , draft] = wrapper.emitted('addItem')!.at(-1)!
    expect(item).toMatchObject({ requires_certification: false })
    expect(draft).toBeNull()
  })
})
