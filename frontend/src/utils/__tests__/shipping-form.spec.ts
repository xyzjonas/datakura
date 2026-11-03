import { describe, expect, it } from 'vitest'
import type { ContactPersonSchema, OutboundOrderShippingSchema } from '@/client'
import {
  emptyShippingForm,
  addressFromContact,
  shippingFormFromShipping,
  toShippingUpsertBody,
} from '../shipping-form'

const type = { id: 3, name: 'Balík PPL', created: '2026-01-01', changed: '2026-01-01' }

const contact = {
  title_pre: 'Ing.',
  first_name: 'Svitlana',
  last_name: 'Zherstenko',
  street: 'Tři Dvory 98',
  city: 'LITOVEL',
  postal_code: '78401',
  state: 'SK',
  email: 'zherstenko@brazzale.cz',
  phone: '+420 770 181 044',
} as ContactPersonSchema

describe('addressFromContact', () => {
  it('maps the contact to the address fields', () => {
    expect(addressFromContact(contact)).toEqual({
      name: 'Ing. Svitlana Zherstenko',
      state: 'SK',
      city: 'LITOVEL',
      street: 'Tři Dvory 98',
      postal_code: '78401',
      email: 'zherstenko@brazzale.cz',
      phone: '+420 770 181 044',
    })
  })

  it.each([null, undefined])('is empty without a contact (%s)', (value) => {
    expect(addressFromContact(value)).toEqual({})
  })

  it('falls back to blanks and CZ for a contact without an address', () => {
    const address = addressFromContact({
      first_name: 'Jan',
      last_name: 'Novák',
      street: null,
      state: null,
    } as ContactPersonSchema)
    expect(address).toMatchObject({ name: 'Jan Novák', street: '', city: '', state: 'CZ' })
  })
})

describe('shippingFormFromShipping', () => {
  it('keeps an empty shipping type empty', () => {
    const form = shippingFormFromShipping({
      id: 1,
      shipping_type: null,
    } as OutboundOrderShippingSchema)
    expect(form.shipping_type).toBeNull()
  })

  it('maps the stored shipping 1:1 and normalizes missing values', () => {
    const form = shippingFormFromShipping({
      id: 1,
      shipping_type: type,
      package_number: '123',
      width: 10,
      name: 'X',
      state: '',
    } as OutboundOrderShippingSchema)
    expect(form).toMatchObject({
      shipping_type: type,
      package_number: '123',
      width: 10,
      height: null,
      price: null,
      name: 'X',
      state: 'CZ',
    })
  })
})

describe('toShippingUpsertBody', () => {
  it('allows an empty shipping type', () => {
    expect(toShippingUpsertBody(emptyShippingForm())).toMatchObject({ shipping_type_id: null })
  })

  it('sends the type id and never the weight', () => {
    const body = toShippingUpsertBody({ ...emptyShippingForm(), shipping_type: type })
    expect(body).toMatchObject({ shipping_type_id: 3 })
    expect(body).not.toHaveProperty('shipping_type')
    expect(body).not.toHaveProperty('weight')
  })

  it.each([
    ['', null],
    [null, null],
    ['12.5', 12.5],
    [0, 0],
    ['abc', null],
  ])('normalizes number input %j to %j', (input, expected) => {
    const body = toShippingUpsertBody({
      ...emptyShippingForm(),
      shipping_type: type,
      width: input as number | null,
      price: input as number | null,
    })
    expect(body?.width).toBe(expected)
    expect(body?.price).toBe(expected)
  })
})
