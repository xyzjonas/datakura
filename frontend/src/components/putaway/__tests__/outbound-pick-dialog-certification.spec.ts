import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { OutboundWarehouseOrderItemSchema } from '@/client'

installQuasarPlugin()

const lookupMock = vi.fn()
const assignMock = vi.fn()
const infoMock = vi.fn()

vi.mock('@/client', () => ({
  warehouseApiRoutesProductGetProductWarehouseInfo: (...a: unknown[]) => infoMock(...a),
  warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem: (...a: unknown[]) =>
    assignMock(...a),
}))
vi.mock('@/composables/use-api', () => ({
  useApi: () => ({ onResponse: (r: { data: unknown }) => r.data }),
}))
vi.mock('@/composables/use-app-settings', () => ({
  useAppSettings: () => ({ scannerMode: ref(false) }),
}))
vi.mock('@/composables/use-barcode-lookup', () => ({
  useBarcodeLookup: () => ({
    lookup: lookupMock,
    loading: ref(false),
    error: ref(null),
  }),
}))

import OutboundWarehousePickDialog from '../OutboundWarehousePickDialog.vue'

const warehouseItem = (id: number, certification: { id: number; code: string } | null) => ({
  id,
  amount: 5,
  unit_of_measure: 'ks',
  tracking_level: 'SERIALIZED_PACKAGE',
  product: { name: 'Matice', code: 'P1' },
  location: { code: `L-${id}`, warehouse_name: 'Sklad' },
  batch: certification ? { id: 1, certification } : null,
})

const orderItem = (patch: Partial<OutboundWarehouseOrderItemSchema> = {}) =>
  ({
    id: 1,
    amount: '2',
    product: { name: 'Matice', code: 'P1', unit: 'ks' },
    desired_package_type_name: null,
    desired_batch_code: null,
    required_origin_country: null,
    ...patch,
  }) as unknown as OutboundWarehouseOrderItemSchema

const stubs = {
  QDialog: { template: '<div><slot /></div>' },
  QCard: { template: '<div><slot /></div>' },
  QInnerLoading: true,
  PackageTypeBadge: true,
  BatchBadge: true,
  CountryBadge: true,
  WarehouseItemAmountBadge: true,
  WarehouseItemTypeBadgeGroup: true,
}

const mountIt = async (item: OutboundWarehouseOrderItemSchema, candidates: unknown[] = []) => {
  infoMock.mockResolvedValue({
    data: { data: [{ locations: [{ items: candidates }] }] },
  })
  const wrapper = mount(OutboundWarehousePickDialog, {
    props: { warehouseOrderCode: 'W1', item, show: false },
    global: { stubs },
  })
  await wrapper.setProps({ show: true })
  await flushPromises()
  return wrapper
}

const scan = async (wrapper: Awaited<ReturnType<typeof mountIt>>, scanned: unknown) => {
  lookupMock.mockResolvedValue({
    found: true,
    entity_type: 'warehouse_item',
    warehouse_item: scanned,
  })
  await wrapper
    .findAll('button')
    .find((b) => b.text().includes('Naskenovat'))!
    .trigger('click')
  await wrapper.get('input').setValue('ABC123')
  await flushPromises()
}

const confirmButton = (wrapper: Awaited<ReturnType<typeof mountIt>>) =>
  wrapper.findAll('button').find((b) => b.text().includes('potvrdit výběr'))!

const cert = { id: 1, code: 'ISO-9001' }

describe('OutboundWarehousePickDialog - certified goods', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    assignMock.mockResolvedValue({ data: { success: true } })
  })

  it('highlights locations with certified goods when no certification is requested', async () => {
    const wrapper = await mountIt(orderItem(), [warehouseItem(1, cert), warehouseItem(2, null)])

    const highlighted = wrapper.findAll('[data-test="certified-location"]')
    expect(highlighted).toHaveLength(1)
    expect(highlighted[0]!.text()).toContain('L-1')
    expect(highlighted[0]!.text()).toContain('ISO-9001')
  })

  it('does not highlight when a batch (certification) is requested', async () => {
    const wrapper = await mountIt(orderItem({ desired_batch_code: 'BAT-1' }), [
      warehouseItem(1, cert),
    ])

    expect(wrapper.find('[data-test="certified-location"]').exists()).toBe(false)
  })

  it('requires an explicit confirmation to pick unrequested certified goods', async () => {
    const wrapper = await mountIt(orderItem(), [warehouseItem(1, cert)])
    await scan(wrapper, warehouseItem(1, cert))

    expect(wrapper.find('[data-test="unrequested-certification-warning"]').exists()).toBe(true)
    expect(confirmButton(wrapper).attributes('disabled')).toBeDefined()

    await confirmButton(wrapper).trigger('click')
    expect(assignMock).not.toHaveBeenCalled()

    await wrapper.get('[data-test="confirm-unrequested-certification"]').trigger('click')
    expect(confirmButton(wrapper).attributes('disabled')).toBeUndefined()

    await confirmButton(wrapper).trigger('click')
    await flushPromises()
    expect(assignMock).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['uncertified goods', orderItem(), warehouseItem(1, null)],
    [
      'requested certified goods',
      orderItem({ desired_batch_code: 'BAT-1' }),
      warehouseItem(1, cert),
    ],
  ])('does not warn for %s', async (_label, item, scanned) => {
    const wrapper = await mountIt(item, [])
    await scan(wrapper, scanned)

    expect(wrapper.find('[data-test="unrequested-certification-warning"]').exists()).toBe(false)
    expect(confirmButton(wrapper).attributes('disabled')).toBeUndefined()
  })
})
