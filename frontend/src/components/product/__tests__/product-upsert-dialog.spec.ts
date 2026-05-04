import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProductUpsertDialog from '../ProductUpsertDialog.vue'

installQuasarPlugin()

describe('ProductUpsertDialog', () => {
  it('emits no_discount value from submit payload', async () => {
    const wrapper = mount(ProductUpsertDialog, {
      props: {
        show: true,
        modelValue: {
          name: 'Produkt',
          code: 'PRD-1',
          type: 'Finished Good',
          unit: 'KS',
          group: '',
          unit_weight: 0,
          base_price: 100,
          purchase_price: 50,
          no_discount: false,
          currency: 'CZK',
          customs_declaration_group: '',
          attributes: {},
        },
      },
      global: {
        stubs: {
          ProductGroupSelect: { template: '<div />' },
          ProductTypeSelect: { template: '<div />' },
          UnitOfMeasureSelect: { template: '<div />' },
          QDialog: { template: '<div><slot /></div>' },
          QCard: { template: '<div><slot /></div>' },
          QForm: { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
          QInput: { template: '<input />' },
          QBtn: { template: '<button><slot /></button>' },
          QTooltip: { template: '<span><slot /></span>' },
          QList: { template: '<div><slot /></div>' },
          QItem: { template: '<div><slot /></div>' },
          QItemSection: { template: '<div><slot /></div>' },
          QToggle: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              '<label><input data-test="no-discount" type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /></label>',
          },
        },
      },
    })

    await wrapper.find('[data-test="no-discount"]').setValue(true)
    await wrapper.find('form').trigger('submit')

    const submitEvents = wrapper.emitted('submit')
    expect(submitEvents).toBeTruthy()
    expect(submitEvents?.[0]?.[0]).toMatchObject({ no_discount: true })
  })
})
