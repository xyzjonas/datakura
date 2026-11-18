import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReturnedItemScanDialog from '../ReturnedItemScanDialog.vue'

installQuasarPlugin()

const { match, claim } = vi.hoisted(() => ({ match: vi.fn(), claim: vi.fn() }))

vi.mock('@/client', () => ({
  warehouseApiRoutesWarehouseMatchReturnedItem: match,
  warehouseApiRoutesWarehouseClaimReturnedItem: claim,
}))
vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (res: { ok: boolean; data?: unknown }) => (res.ok ? res.data : undefined),
  }),
}))

const matchedItem = {
  order_item_id: 7,
  warehouse_item: {
    id: 42,
    primary_barcode: 'BOX-1',
    amount: 1,
    outbound_order_code: 'V001',
    product: { code: 'P1', name: 'Box', unit: 'KS' },
  },
}

const mountDialog = () =>
  mount(ReturnedItemScanDialog, {
    props: { show: true, orderCode: 'PV001' },
    global: { stubs: { QDialog: { template: '<div><slot /></div>' } } },
  })

beforeEach(() => vi.clearAllMocks())

describe('ReturnedItemScanDialog', () => {
  it('cannot search for an empty barcode', () => {
    const wrapper = mountDialog()

    expect(
      wrapper.get('[data-test="returned-item-match-btn"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('offers the matched item, then claims exactly that item and the offered line', async () => {
    match.mockResolvedValue({ ok: true, data: { data: matchedItem } })
    claim.mockResolvedValue({ ok: true, data: { data: { code: 'PV001' } } })
    const wrapper = mountDialog()

    await wrapper.get('input[data-test="returned-item-barcode"]').setValue(' BOX-1 ')
    await wrapper.get('[data-test="returned-item-match-btn"]').trigger('click')
    await flushPromises()

    expect(match).toHaveBeenCalledWith({ path: { code: 'PV001' }, body: { barcode: 'BOX-1' } })
    expect(wrapper.get('[data-test="returned-item-match"]').text()).toContain('BOX-1')
    expect(wrapper.get('[data-test="returned-item-match"]').text()).toContain('V001')

    await wrapper.get('[data-test="returned-item-claim"]').trigger('click')
    await flushPromises()

    expect(claim).toHaveBeenCalledWith({
      path: { code: 'PV001' },
      body: { order_item_id: 7, warehouse_item_id: 42 },
    })
    expect(wrapper.emitted('claimed')).toEqual([[{ code: 'PV001' }]])
    expect(wrapper.emitted('update:show')).toEqual([[false]])
  })

  it('shows an error and offers nothing when the barcode is not a returnable item', async () => {
    match.mockResolvedValue({ ok: false })
    const wrapper = mountDialog()

    await wrapper.get('input[data-test="returned-item-barcode"]').setValue('NOPE')
    await wrapper.get('[data-test="returned-item-match-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="returned-item-match"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="returned-item-claim"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('nenalezena')
    expect(claim).not.toHaveBeenCalled()
  })

  it('does not close or emit when the claim is rejected', async () => {
    match.mockResolvedValue({ ok: true, data: { data: matchedItem } })
    claim.mockResolvedValue({ ok: false })
    const wrapper = mountDialog()
    await wrapper.get('input[data-test="returned-item-barcode"]').setValue('BOX-1')
    await wrapper.get('[data-test="returned-item-match-btn"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="returned-item-claim"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('claimed')).toBeUndefined()
    expect(wrapper.emitted('update:show')).toBeUndefined()
  })
})
