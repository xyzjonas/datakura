import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PackageTypeUpsertDialog from '../PackageTypeUpsertDialog.vue'

installQuasarPlugin()

describe('PackageTypeUpsertDialog', () => {
  it('normalizes optional fields on submit', async () => {
    const wrapper = mount(PackageTypeUpsertDialog, {
      props: {
        show: true,
        modelValue: {
          name: 'BOX-10',
          description: '   ',
          amount: 10,
          unit: '',
        },
      },
      global: {
        stubs: {
          QDialog: {
            template: '<div><slot /></div>',
          },
          QCard: {
            template: '<div><slot /></div>',
          },
          QForm: {
            template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>',
          },
          QInput: {
            template: '<input />',
          },
          QBtn: {
            template: '<button><slot /></button>',
          },
          UnitOfMeasureSelect: {
            template: '<div />',
          },
        },
      },
    })

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')?.at(-1)).toEqual([
      {
        name: 'BOX-10',
        description: null,
        amount: 10,
        unit: null,
      },
    ])
  })
})
