import type { OutboundOrderItemSchema } from '@/client'
import { provideReturnSelection, type ReturnSelection } from '@/composables/use-return-selection'
import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, type PropType } from 'vue'
import CloseIconButton from '../../common/buttons/CloseIconButton.vue'
import EditIconButton from '../../common/buttons/EditIconButton.vue'
import OutboundItemReturnControl from '../OutboundItemReturnControl.vue'
import OutboundOrderItemRowCompact from '../OutboundOrderItemRowCompact.vue'
import OutboundReturnBar from '../OutboundReturnBar.vue'
import OutboundReturnToggleButton from '../OutboundReturnToggleButton.vue'
import ReturnItemDialog from '../ReturnItemDialog.vue'

installQuasarPlugin()

const makeItem = (overrides: Partial<OutboundOrderItemSchema> = {}) =>
  ({
    index: 0,
    amount: 10,
    returned_amount: 0,
    is_returned: false,
    unit_price: 100,
    total_price: 1000,
    document_unit_price: 100,
    document_total_price: 1000,
    product: { code: 'P1', name: 'Prod', unit: 'KS', purchase_price: 60 },
    pricing_details: {
      base_price: 100,
      avg_purchase_price: 60,
      suggested_unit_price: 100,
      selected_unit_price: 100,
      discount_percent: 0,
      reason: 'Base',
      source: 'BASE_PRICE',
      margin_amount: 40,
      margin_percent: 0,
    },
    ...overrides,
  }) as unknown as OutboundOrderItemSchema

/** Provides the selection of the surrounding order, like the order view does. */
const withSelection = (child: ReturnType<typeof defineComponent>, active = true) => {
  const state: { selection?: ReturnSelection } = {}
  const Host = defineComponent({
    props: { item: { type: Object as PropType<OutboundOrderItemSchema>, required: true } },
    setup(props) {
      state.selection = provideReturnSelection()
      state.selection.active.value = active
      return () =>
        h(child, {
          item: props.item,
          currency: 'CZK',
          baseCurrency: 'CZK',
          exchangeRate: 1,
          orderCode: 'OP1',
        })
    },
  })
  return { Host, state }
}

const stubs = {
  RouterLink: true,
  ProductAvailability: true,
  OutboundOrderItemEditDialog: true,
  ReturnItemDialog: true,
  QPopupProxy: true,
}

describe('returned row', () => {
  const mountRow = (item: OutboundOrderItemSchema) => {
    const { Host } = withSelection(OutboundOrderItemRowCompact as never, false)
    return mount(Host, { props: { item }, global: { stubs } })
  }

  it('is marked as returned, negative and without margin or actions', () => {
    const wrapper = mountRow(
      makeItem({ is_returned: true, amount: 4, total_price: 400, document_total_price: 400 }),
    )

    expect(wrapper.find('[data-test="returned-badge"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('-400.00')
    expect(wrapper.get('[data-test="item-margin"]').text()).toBe('')
    expect(wrapper.findComponent(EditIconButton).exists()).toBe(false)
    expect(wrapper.findComponent(CloseIconButton).exists()).toBe(false)
  })

  it('sold row has no badge and keeps its margin and actions', () => {
    const wrapper = mountRow(makeItem())

    expect(wrapper.find('[data-test="returned-badge"]').exists()).toBe(false)
    expect(wrapper.get('[data-test="item-margin"]').text()).not.toBe('')
    expect(wrapper.findComponent(EditIconButton).exists()).toBe(true)
    expect(wrapper.findComponent(CloseIconButton).exists()).toBe(true)
  })
})

describe('OutboundItemReturnControl', () => {
  const mountControl = (item: OutboundOrderItemSchema, active = true) => {
    const { Host, state } = withSelection(OutboundItemReturnControl as never, active)
    const wrapper = mount(Host, { props: { item }, global: { stubs } })
    return { wrapper, selection: state.selection! }
  }

  it('is hidden outside of the selection mode', () => {
    const { wrapper } = mountControl(makeItem(), false)

    expect(wrapper.find('[data-test="return-item-button"]').exists()).toBe(false)
  })

  it.each([
    ['fully returned', { returned_amount: 10 }],
    ['a returned row', { is_returned: true }],
    [
      'a non-physical product',
      { product: { code: 'S', name: 'S', unit: 'KS', non_physical: true } },
    ],
  ])('offers nothing for %s', (_label, overrides) => {
    const { wrapper } = mountControl(makeItem(overrides as Partial<OutboundOrderItemSchema>))

    expect(wrapper.find('[data-test="return-item-button"]').exists()).toBe(false)
  })

  it('collects the confirmed amount into the batch and can take it back out', async () => {
    const { wrapper, selection } = mountControl(makeItem({ index: 2, returned_amount: 4 }))
    const dialog = wrapper.findComponent(ReturnItemDialog)
    expect(dialog.props('max')).toBe(6) // 10 sold - 4 already returned

    dialog.vm.$emit('update:amount', 3)
    await wrapper.vm.$nextTick()

    expect(selection.lines.value).toEqual([{ item_index: 2, amount: 3 }])
    expect(wrapper.get('[data-test="return-batch-badge"]').text()).toContain('3 KS')

    await wrapper.get('[data-test="return-item-remove"]').trigger('click')
    expect(selection.count.value).toBe(0)
    expect(wrapper.find('[data-test="return-batch-badge"]').exists()).toBe(false)
  })
})

describe('ReturnItemDialog', () => {
  const mountDialog = (max = 6, amount = 0) =>
    mount(ReturnItemDialog, {
      props: { show: true, amount, max, item: makeItem() },
      global: { stubs: { QDialog: { template: '<div><slot /></div>' } } },
    })

  it('cannot confirm an amount above what is left or non-positive', async () => {
    const wrapper = mountDialog()
    const input = wrapper.get('input[data-test="return-amount-input"]')

    for (const bad of ['7', '0', '-1', '']) {
      await input.setValue(bad)
      expect(wrapper.get('[data-test="return-confirm"]').attributes('disabled')).toBeDefined()
    }
  })

  it('confirms a valid amount and closes', async () => {
    const wrapper = mountDialog()

    await wrapper.get('input[data-test="return-amount-input"]').setValue('2.5')
    await wrapper.get('[data-test="return-confirm"]').trigger('click')

    expect(wrapper.emitted('update:amount')).toEqual([[2.5]])
    expect(wrapper.emitted('update:show')).toEqual([[false]])
  })

  it('"vrátit vše" fills the most that is left', async () => {
    const wrapper = mountDialog(6)

    await wrapper.get('[data-test="return-all"]').trigger('click')
    await wrapper.get('[data-test="return-confirm"]').trigger('click')

    expect(wrapper.emitted('update:amount')).toEqual([[6]])
  })
})

describe('return bar and toggle', () => {
  const mountWithSelection = (component: unknown, props: Record<string, unknown>) => {
    const state: { selection?: ReturnSelection } = {}
    const Host = defineComponent({
      setup() {
        state.selection = provideReturnSelection()
        return () => h(component as never, props)
      },
    })
    return { wrapper: mount(Host), selection: state.selection! }
  }

  it('toggle switches the mode on and off, dropping the batch', async () => {
    const { wrapper, selection } = mountWithSelection(OutboundReturnToggleButton, {})

    await wrapper.get('[data-test="return-toggle"]').trigger('click')
    expect(selection.active.value).toBe(true)

    selection.set(0, 1)
    await wrapper.get('[data-test="return-toggle"]').trigger('click')
    expect(selection.active.value).toBe(false)
    expect(selection.count.value).toBe(0)
  })

  it('bar is only shown in the selection mode and apply needs a selection', async () => {
    const { wrapper, selection } = mountWithSelection(OutboundReturnBar, {
      value: 250,
      currency: 'CZK',
    })
    expect(wrapper.find('[data-test="return-bar"]').exists()).toBe(false)

    selection.active.value = true
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-test="return-apply"]').attributes('disabled')).toBeDefined()

    selection.set(0, 2)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-test="return-apply"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-test="return-value"]').text()).toContain('250')
  })

  it('cancel leaves the mode without applying', async () => {
    const { wrapper, selection } = mountWithSelection(OutboundReturnBar, {
      value: 0,
      currency: 'CZK',
    })
    selection.active.value = true
    selection.set(0, 2)
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-test="return-cancel"]').trigger('click')

    expect(selection.active.value).toBe(false)
    expect(selection.count.value).toBe(0)
  })
})
