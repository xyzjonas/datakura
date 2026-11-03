import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { OutboundOrderShippingSchema } from '@/client'
import ShippingCard from '../ShippingCard.vue'

installQuasarPlugin()

const stubs = {
  ForegroundPanel: { template: '<div><slot name="header" /><slot /></div>' },
  QBtn: { template: '<button type="button"><slot /></button>' },
  QIcon: { template: '<i />' },
  QTooltip: { template: '<span />' },
  CopyToClipBoardButton: { template: '<span />' },
}

const shipping = {
  id: 1,
  shipping_type: { id: 1, name: 'Balík PPL', created: '', changed: '' },
  package_number: 'PKG-1',
  width: 10,
  height: 20,
  depth: 30,
  name: 'Svitlana Zherstenko',
  state: 'CZ',
  city: 'LITOVEL',
  street: 'Tři Dvory 98',
  postal_code: '78401',
  email: 'zherstenko@brazzale.cz',
  phone: '+420 770 181 044',
  price: 100,
  price_with_vat: 121,
  created: '',
  changed: '',
} as OutboundOrderShippingSchema

const mountCard = (props: Partial<InstanceType<typeof ShippingCard>['$props']> = {}) =>
  mount(ShippingCard, {
    props: { shipping, weight: 35.1, currency: 'CZK', editable: true, ...props },
    global: { stubs },
  })

describe('ShippingCard', () => {
  it('shows an empty state with a create action when there is no shipping', async () => {
    const wrapper = mountCard({ shipping: null })

    expect(wrapper.find('[data-testid="shipping-empty"]').exists()).toBe(true)
    await wrapper.find('[data-testid="shipping-empty"] button').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
  })

  it('hides the create action when not editable', () => {
    const wrapper = mountCard({ shipping: null, editable: false })

    expect(wrapper.find('[data-testid="shipping-empty"] button').exists()).toBe(false)
  })

  it('renders type, dimensions, derived weight, address and prices', () => {
    const wrapper = mountCard()

    expect(wrapper.text()).toContain('Balík PPL')
    expect(wrapper.text()).toContain('PKG-1')
    expect(wrapper.get('[data-testid="shipping-dimensions"]').text()).toBe('10 × 20 × 30 cm')
    expect(wrapper.get('[data-testid="shipping-weight"]').text()).toBe('35.10 g')
    expect(wrapper.get('[data-testid="shipping-address"]').text()).toContain('78401 LITOVEL')
    expect(wrapper.get('[data-testid="shipping-price-vat"]').text()).toContain('CZK')
  })

  it('handles missing dimensions and prices', () => {
    const wrapper = mountCard({
      shipping: {
        ...shipping,
        width: null,
        height: null,
        depth: null,
        price: null,
        price_with_vat: null,
        package_number: '',
      },
    })

    expect(wrapper.get('[data-testid="shipping-dimensions"]').text()).toBe('rozměry nezadány')
    expect(wrapper.text()).toContain('Cena nezadána')
    expect(wrapper.text()).not.toContain('číslo balíku')
  })

  it('emits edit and remove', async () => {
    const wrapper = mountCard()

    await wrapper.get('[data-testid="shipping-edit"]').trigger('click')
    await wrapper.get('[data-testid="shipping-remove"]').trigger('click')

    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('remove')).toHaveLength(1)
  })

  it('has no actions when not editable', () => {
    const wrapper = mountCard({ editable: false })

    expect(wrapper.find('[data-testid="shipping-edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="shipping-remove"]').exists()).toBe(false)
  })
})
