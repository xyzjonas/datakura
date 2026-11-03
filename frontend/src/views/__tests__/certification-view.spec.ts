import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, Suspense } from 'vue'
import CertificationView from '../CertificationView.vue'

const { getCertMock, getItemsMock } = vi.hoisted(() => ({
  getCertMock: vi.fn(),
  getItemsMock: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesCertificationsGetCertification: getCertMock,
  warehouseApiRoutesCertificationsGetCertificationItems: getItemsMock,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown; response: Response }) =>
      response.response.ok ? response.data : undefined,
  }),
}))

installQuasarPlugin()

const respond = (data: unknown, status = 200) => ({
  data: status === 200 ? { success: true, data } : undefined,
  error: status === 200 ? undefined : {},
  request: new Request('http://localhost/x'),
  response: new Response(null, { status }),
})

const certification = {
  id: 7,
  code: 'ISO-9001',
  description: 'Material strength',
  attachment: { name: 'iso.pdf', url: '/media/certifications/iso.pdf' },
  batch_codes: ['BAT-1', 'BAT-2'],
}

const stockItem = (id: number, batch: string, amount: number) => ({
  id,
  amount,
  tracking_level: 'FUNGIBLE',
  product: { code: 'P1', name: 'Šroub M8' },
  location: { code: 'A-01', warehouse_name: 'W' },
  package: null,
  batch: { id: id, primary_barcode: { code: batch }, certification: { id: 7, code: 'ISO-9001' } },
})

const mountView = async () => {
  const wrapper = mount(
    defineComponent({
      render: () => h(Suspense, null, { default: () => h(CertificationView, { id: '7' }) }),
    }),
    {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' }, QBreadcrumbs: true },
      },
    },
  )
  await flushPromises()
  return wrapper
}

describe('CertificationView', () => {
  beforeEach(() => {
    getCertMock.mockReset()
    getItemsMock.mockReset()
  })

  it('loads the certification and its stock by id', async () => {
    getCertMock.mockResolvedValue(respond(certification))
    getItemsMock.mockResolvedValue(respond([]))

    await mountView()

    expect(getCertMock).toHaveBeenCalledWith({ path: { certification_id: 7 } })
    expect(getItemsMock).toHaveBeenCalledWith({ path: { certification_id: 7 } })
  })

  it('shows the certification with a file link opening in a new tab', async () => {
    getCertMock.mockResolvedValue(respond(certification))
    getItemsMock.mockResolvedValue(respond([]))

    const wrapper = await mountView()

    expect(wrapper.get('[data-test="certification-code"]').text()).toBe('ISO-9001')
    expect(wrapper.text()).toContain('Material strength')
    const file = wrapper.get('[data-test="certification-open-file"]')
    expect(file.attributes('href')).toBe('/media/certifications/iso.pdf')
    expect(file.attributes('target')).toBe('_blank')
    expect(wrapper.text()).toContain('BAT-1')
    expect(wrapper.text()).toContain('BAT-2')
  })

  it('lists every warehouse item carrying the certification', async () => {
    getCertMock.mockResolvedValue(respond(certification))
    getItemsMock.mockResolvedValue(respond([stockItem(1, 'BAT-1', 4), stockItem(2, 'BAT-2', 6)]))

    const wrapper = await mountView()

    expect(wrapper.get('[data-test="items-count"]').text()).toContain('2')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.text()).toContain('Šroub M8')
    expect(wrapper.text()).toContain('A-01')
  })

  it('shows an empty state when nothing is in stock', async () => {
    getCertMock.mockResolvedValue(respond(certification))
    getItemsMock.mockResolvedValue(respond([]))

    const wrapper = await mountView()

    expect(wrapper.get('[data-test="items-count"]').text()).toContain('0')
    expect(wrapper.text()).toContain('Žádné zboží s touto certifikací')
  })

  it('handles a certification without attachment', async () => {
    getCertMock.mockResolvedValue(respond({ ...certification, attachment: null }))
    getItemsMock.mockResolvedValue(respond([]))

    const wrapper = await mountView()

    expect(wrapper.find('[data-test="certification-open-file"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('bez přílohy')
  })

  it('renders a 404 for an unknown certification', async () => {
    getCertMock.mockResolvedValue(respond(undefined, 404))
    getItemsMock.mockResolvedValue(respond(undefined, 404))

    const wrapper = await mountView()

    expect(wrapper.text()).toContain('CERTIFIKACE NENALEZENA')
    expect(wrapper.find('[data-test="certification-detail"]').exists()).toBe(false)
  })
})
