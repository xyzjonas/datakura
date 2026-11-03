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

// exposes the (computed) options and emits like Quasar does
const QSelectStub = {
  props: ['modelValue', 'options'],
  emits: ['filter', 'input-value', 'update:modelValue'],
  template: `<div>
    <span v-for="opt in options" :key="opt.id" :data-testid="opt.isCreate ? 'create' : 'opt'">
      {{ opt.name }}
    </span>
  </div>`,
}

const mountSelect = () =>
  mount(ShippingTypeSelect, {
    props: { modelValue: null },
    global: { stubs: { QSelect: QSelectStub } },
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

  it('offers the creation as the last option for an unknown name', async () => {
    const wrapper = mountSelect()

    await type(wrapper, 'Kurýr')

    expect(wrapper.findAll('[data-testid="opt"]')).toHaveLength(1)
    expect(wrapper.get('[data-testid="create"]').text()).toBe('Kurýr')
  })

  it('offers the creation even when no type matches at all', async () => {
    getTypes.mockResolvedValue({ data: { data: [] } })
    const wrapper = mountSelect()

    await type(wrapper, 'Kurýr')

    expect(wrapper.find('[data-testid="create"]').exists()).toBe(true)
  })

  it.each(['', '   ', 'balík ppl', 'Balík PPL'])(
    'does not offer creation for %j (empty or exact match)',
    async (text) => {
      const wrapper = mountSelect()

      await type(wrapper, text)

      expect(wrapper.find('[data-testid="create"]').exists()).toBe(false)
    },
  )

  it('creates the type when the create option is picked and selects it', async () => {
    const created = { id: 2, name: 'Kurýr', created: '', changed: '' }
    createType.mockResolvedValue({ data: { data: created } })
    const wrapper = mountSelect()
    await type(wrapper, '  Kurýr ')
    const createOption = wrapper.getComponent(QSelectStub).props('options').at(-1)

    wrapper.getComponent(QSelectStub).vm.$emit('update:modelValue', createOption)
    await flushPromises()

    expect(createType).toHaveBeenCalledWith({ body: { name: 'Kurýr' } })
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([created])
  })

  it('selects an existing type without creating anything', async () => {
    const wrapper = mountSelect()
    await type(wrapper, 'Bal')

    wrapper.getComponent(QSelectStub).vm.$emit('update:modelValue', existing)
    await flushPromises()

    expect(createType).not.toHaveBeenCalled()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([existing])
  })

  it('keeps the selection untouched when the creation fails', async () => {
    createType.mockResolvedValue({ data: undefined })
    const wrapper = mountSelect()
    await type(wrapper, 'Kurýr')
    const createOption = wrapper.getComponent(QSelectStub).props('options').at(-1)

    wrapper.getComponent(QSelectStub).vm.$emit('update:modelValue', createOption)
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
