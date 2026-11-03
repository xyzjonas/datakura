import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ShippingTypeSelect from '../ShippingTypeSelect.vue'

installQuasarPlugin()

const existing = { id: 1, name: 'Balík PPL', created: '', changed: '' }

const { getTypes, createType } = vi.hoisted(() => ({
  getTypes: vi.fn(),
  createType: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesShippingTypesGetShippingTypes: getTypes,
  warehouseApiRoutesShippingTypesCreateShippingType: createType,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: (res: { data?: unknown }) => res.data }),
}))

// the select exposes its slots + emits `filter` / `input-value` like Quasar does
const QSelectStub = {
  props: ['modelValue', 'options'],
  emits: ['filter', 'input-value', 'update:modelValue'],
  template: `<div>
    <slot name="no-option" />
    <slot name="after-options" />
  </div>`,
}

const mountSelect = () =>
  mount(ShippingTypeSelect, {
    props: { modelValue: null },
    global: { stubs: { QSelect: QSelectStub, QItem: { template: '<div><slot /></div>' } } },
  })

const type = async (wrapper: ReturnType<typeof mountSelect>, text: string) => {
  const select = wrapper.getComponent(QSelectStub)
  select.vm.$emit('input-value', text)
  select.vm.$emit('filter', text, (cb: () => void) => cb())
  await flushPromises()
}

describe('ShippingTypeSelect', () => {
  beforeEach(() => {
    getTypes.mockReset()
    createType.mockReset()
    getTypes.mockResolvedValue({ data: { data: [existing] } })
  })

  it('offers the creation of a type that does not exist yet', async () => {
    const wrapper = mountSelect()

    await type(wrapper, 'Kurýr')

    expect(wrapper.get('[data-testid="shipping-type-create"]').text()).toContain('Kurýr')
  })

  it.each(['', '   ', 'balík ppl', 'Balík PPL'])(
    'does not offer creation for %j (empty or exact match)',
    async (text) => {
      const wrapper = mountSelect()

      await type(wrapper, text)

      expect(wrapper.find('[data-testid="shipping-type-create"]').exists()).toBe(false)
    },
  )

  it('creates the typed type and selects it', async () => {
    const created = { id: 2, name: 'Kurýr', created: '', changed: '' }
    createType.mockResolvedValue({ data: { data: created } })
    const wrapper = mountSelect()
    await type(wrapper, '  Kurýr ')

    await wrapper.get('[data-testid="shipping-type-create"]').trigger('click')
    await flushPromises()

    expect(createType).toHaveBeenCalledWith({ body: { name: 'Kurýr' } })
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([created])
  })

  it('keeps the selection untouched when the creation fails', async () => {
    createType.mockResolvedValue({ data: undefined })
    const wrapper = mountSelect()
    await type(wrapper, 'Kurýr')

    await wrapper.get('[data-testid="shipping-type-create"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
