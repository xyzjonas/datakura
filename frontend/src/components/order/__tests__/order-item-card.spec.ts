import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { calculateMargin } from '@/utils/margin'
import OrderItemCard from '../OrderItemCard.vue'
import CloseIconButton from '../../common/buttons/CloseIconButton.vue'
import EditIconButton from '../../common/buttons/EditIconButton.vue'

installQuasarPlugin()

const item = (overrides = {}) => ({
  index: 0,
  amount: 10,
  total_price: 21200,
  note: null,
  product: { code: '0981-0400-00', name: 'Matice', unit: 'ks' },
  ...overrides,
})

const mountCard = (props = {}) =>
  mount(OrderItemCard, {
    props: { item: item(), currency: 'CZK', purchasePrice: 791.8, ...props },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })

describe('OrderItemCard', () => {
  it('shows no certification badge by default (e.g. outbound items)', () => {
    expect(mountCard().find('[data-test="certification-badge"]').exists()).toBe(false)
  })

  it('flags a certified item that still misses its certificate', () => {
    const wrapper = mountCard({ requiresCertification: true, certification: null })
    expect(wrapper.get('[data-test="certification-badge"]').text()).toContain('chybí certifikát')
  })

  it('shows the certificate code once supplied', () => {
    const wrapper = mountCard({ requiresCertification: true, certification: { code: 'EN-10204' } })
    expect(wrapper.get('[data-test="certification-badge"]').text()).toContain('EN-10204')
  })

  it('renders index, product and Czech formatted prices', () => {
    const wrapper = mountCard({ sellingPrice: 2120 })
    expect(wrapper.get('[data-test="item-index"]').text()).toBe('#1')
    expect(wrapper.text()).toContain('Matice')
    expect(wrapper.text()).toContain('0981-0400-00')
    expect(wrapper.get('[data-test="item-purchase-price"]').text()).toContain('791,80')
    expect(wrapper.get('[data-test="item-unit-price"]').text()).toContain('2')
    expect(wrapper.get('[data-test="item-unit-price"]').text()).toContain('120,00')
    expect(wrapper.get('[data-test="item-total-price"]').text().replace(/\s/g, '')).toBe(
      '21200,00CZK',
    )
  })

  it.each([
    [100, 60, 'text-green-600', '+40,00'],
    [50, 80, 'text-red', '-30,00'],
  ])('colors margin for selling %s / purchase %s', (selling, purchase, cls, amount) => {
    const wrapper = mountCard({
      sellingPrice: selling,
      margin: calculateMargin(selling, purchase),
    })
    const margin = wrapper.get('[data-test="item-margin"]')
    expect(margin.find(`.${cls}`).exists()).toBe(true)
    expect(margin.text()).toContain(amount)
  })

  it('hides selling price and margin for inbound items', () => {
    const wrapper = mountCard()
    expect(wrapper.find('[data-test="item-unit-price"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="item-margin"]').exists()).toBe(false)
  })

  it('emits edit and remove', async () => {
    const wrapper = mountCard()
    await wrapper.findComponent(EditIconButton).find('button').trigger('click')
    await wrapper.findComponent(CloseIconButton).find('button').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('remove')).toHaveLength(1)
  })

  it('disables actions when readonly and shows note', () => {
    const wrapper = mountCard({ readonly: true, item: item({ note: 'Pozor' }) })
    expect(
      wrapper.findComponent(EditIconButton).find('button').attributes('disabled'),
    ).toBeDefined()
    expect(wrapper.text()).toContain('Pozor')
  })
})
