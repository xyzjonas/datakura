import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { ContactPersonSchema } from '@/client'
import { emptyShippingForm, type ShippingForm } from '@/utils/shipping-form'
import ShippingUpsertDialog from '../ShippingUpsertDialog.vue'

installQuasarPlugin()

const type = { id: 3, name: 'Balík PPL', created: '', changed: '' }

const stubs = {
  QDialog: { template: '<div><slot /></div>' },
  QCard: { template: '<div><slot /></div>' },
  QForm: { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
  QInput: {
    props: { modelValue: null, readonly: Boolean },
    template: '<input :value="modelValue" :readonly="readonly" />',
  },
  QSelect: { template: '<select />' },
  QBtn: { template: '<button type="button"><slot /></button>' },
  ShippingTypeSelect: { template: '<div />' },
}

const mountDialog = (form: ShippingForm, props: Record<string, unknown> = {}) =>
  mount(ShippingUpsertDialog, {
    props: { show: true, modelValue: form, weight: 35.1, ...props },
    global: { stubs, directives: { 'close-popup': {} } },
  })

describe('ShippingUpsertDialog', () => {
  it('shows the derived weight as a readonly value', () => {
    const wrapper = mountDialog(emptyShippingForm())

    const weight = wrapper.get('[data-testid=\"shipping-weight\"]').element as HTMLInputElement
    expect(weight.value).toBe('35.10')
    expect(weight.readOnly).toBe(true)
  })

  it('submits the body with the type id', async () => {
    const wrapper = mountDialog({ ...emptyShippingForm(), shipping_type: type, city: 'LITOVEL' })

    await wrapper.find('form').trigger('submit')

    const [[body]] = wrapper.emitted('submit') as unknown as [[Record<string, unknown>]]
    expect(body).toMatchObject({ shipping_type_id: 3, city: 'LITOVEL', width: null })
    expect(body).not.toHaveProperty('weight')
  })

  it('submits even without a shipping type', async () => {
    const wrapper = mountDialog(emptyShippingForm())

    await wrapper.find('form').trigger('submit')

    const [[body]] = wrapper.emitted('submit') as unknown as [[Record<string, unknown>]]
    expect(body).toMatchObject({ shipping_type_id: null })
  })

  it('offers loading the address from the contact only when there is one', async () => {
    const contact = {
      first_name: 'Jan',
      last_name: 'Novák',
      city: 'Praha',
      state: 'CZ',
    } as ContactPersonSchema
    expect(
      mountDialog(emptyShippingForm()).find('[data-testid="shipping-load-contact"]').exists(),
    ).toBe(false)

    const wrapper = mountDialog(
      { ...emptyShippingForm(), shipping_type: type, city: 'Brno' },
      { contact },
    )
    await wrapper.get('[data-testid="shipping-load-contact"]').trigger('click')

    const [updated] = wrapper.emitted('update:modelValue')!.at(-1) as [ShippingForm]
    expect(updated).toMatchObject({ name: 'Jan Novák', city: 'Praha', shipping_type: type })
  })
})
