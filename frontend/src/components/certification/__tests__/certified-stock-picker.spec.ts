import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CertifiedStockPicker from '../CertifiedStockPicker.vue'

const { getAvailableMock } = vi.hoisted(() => ({ getAvailableMock: vi.fn() }))

vi.mock('@/client', () => ({
  warehouseApiRoutesCertificationsGetAvailableCertifications: getAvailableMock,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown; response: Response }) =>
      response.response.ok ? response.data : undefined,
  }),
}))

installQuasarPlugin()

const respond = (data: unknown[]) => ({
  data: { success: true, data },
  error: undefined,
  request: new Request('http://localhost/api/v1/certifications/available'),
  response: new Response(null, { status: 200 }),
})

const rows = [
  {
    id: 1,
    code: 'CERT-A',
    description: 'strength',
    attachment: { name: 'a.pdf', url: '/media/certifications/a.pdf' },
    ordered_date: '2026-03-01T10:00:00Z',
    amount: 12,
    batch_code: 'BAT-A',
  },
  {
    id: 2,
    code: 'CERT-B',
    description: null,
    attachment: null,
    ordered_date: '2026-02-01T10:00:00Z',
    amount: 3,
    batch_code: 'BAT-B',
  },
]

const mountPicker = (modelValue: string | null = null) =>
  mount(CertifiedStockPicker, {
    props: {
      productCode: 'P1',
      modelValue,
      'onUpdate:modelValue': (v: string | null) => wrapperProps.onUpdate(v),
    },
  })

const wrapperProps = { onUpdate: vi.fn() }

describe('CertifiedStockPicker', () => {
  beforeEach(() => {
    getAvailableMock.mockReset()
    wrapperProps.onUpdate.mockReset()
  })

  it('requests certified stock for the given product', async () => {
    getAvailableMock.mockResolvedValue(respond(rows))

    mountPicker()
    await flushPromises()

    expect(getAvailableMock).toHaveBeenCalledWith({ query: { product_code: 'P1' } })
  })

  it('lists certifications with amount and a file link opening in a new tab', async () => {
    getAvailableMock.mockResolvedValue(respond(rows))

    const wrapper = mountPicker()
    await flushPromises()

    const tableRows = wrapper.findAll('[data-test="certified-stock-row"]')
    expect(tableRows).toHaveLength(2)
    expect(tableRows[0]!.text()).toContain('CERT-A')
    expect(tableRows[0]!.text()).toContain('12')
    const link = tableRows[0]!.get('[data-test="certification-file-link"]')
    expect(link.attributes('href')).toBe('/media/certifications/a.pdf')
    expect(link.attributes('target')).toBe('_blank')
    expect(tableRows[1]!.text()).toContain('bez přílohy')
    // icon only - the (possibly long) file name must not widen the dialog
    expect(tableRows[0]!.get('[data-test="certification-file-link"]').text()).not.toContain('a.pdf')
  })

  it('lists a certification spanning several batches as one row per batch', async () => {
    getAvailableMock.mockResolvedValue(
      respond([
        { ...rows[0], batch_code: 'BAT-A1', amount: 7 },
        { ...rows[0], batch_code: 'BAT-A2', amount: 4 },
      ]),
    )

    const wrapper = mountPicker()
    await flushPromises()

    const tableRows = wrapper.findAll('[data-test="certified-stock-row"]')
    expect(tableRows).toHaveLength(2)
    expect(tableRows[0]!.text()).toContain('BAT-A1')
    expect(tableRows[1]!.text()).toContain('BAT-A2')
    await tableRows[1]!.trigger('click')
    expect(wrapperProps.onUpdate).toHaveBeenCalledWith('BAT-A2')
  })

  it('selecting a row emits the batch code of that certification', async () => {
    getAvailableMock.mockResolvedValue(respond(rows))

    const wrapper = mountPicker()
    await flushPromises()
    await wrapper.findAll('[data-test="certified-stock-row"]')[1]!.trigger('click')

    expect(wrapperProps.onUpdate).toHaveBeenCalledWith('BAT-B')
  })

  it('clicking the file link does not select the row', async () => {
    getAvailableMock.mockResolvedValue(respond(rows))

    const wrapper = mountPicker()
    await flushPromises()
    await wrapper.get('[data-test="certification-file-link"]').trigger('click')

    expect(wrapperProps.onUpdate).not.toHaveBeenCalled()
  })

  it('shows an empty state when nothing certified is in stock', async () => {
    getAvailableMock.mockResolvedValue(respond([]))

    const wrapper = mountPicker()
    await flushPromises()

    expect(wrapper.find('[data-test="certified-stock-row"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('žádné certifikované zboží')
  })

  it('shows the empty state when the request fails', async () => {
    getAvailableMock.mockResolvedValue({
      data: undefined,
      error: {},
      request: new Request('http://localhost/x'),
      response: new Response(null, { status: 500 }),
    })

    const wrapper = mountPicker()
    await flushPromises()

    expect(wrapper.find('[data-test="certified-stock-row"]').exists()).toBe(false)
  })
})
