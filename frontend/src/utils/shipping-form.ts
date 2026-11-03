import type {
  ContactPersonSchema,
  OutboundOrderShippingSchema,
  OutboundOrderShippingUpsertSchema,
  ShippingTypeSchema,
} from '@/client'
import { contactFullName } from '@/utils/contact-name'

export const SHIPPING_STATES = ['CZ', 'SK']

/** Editable shipping form; the type is the whole object so the select can show its name. */
export type ShippingForm = {
  shipping_type: ShippingTypeSchema | null
  package_number: string
  width: number | null
  height: number | null
  depth: number | null
  name: string
  state: string
  city: string
  street: string
  postal_code: string
  email: string
  phone: string
  price: number | null
  price_with_vat: number | null
}

export type ShippingAddress = Pick<
  ShippingForm,
  'name' | 'state' | 'city' | 'street' | 'postal_code' | 'email' | 'phone'
>

export const emptyShippingForm = (): ShippingForm => ({
  shipping_type: null,
  package_number: '',
  width: null,
  height: null,
  depth: null,
  name: '',
  state: 'CZ',
  city: '',
  street: '',
  postal_code: '',
  email: '',
  phone: '',
  price: null,
  price_with_vat: null,
})

/** Address as it is seeded from the contact person (mirrors the backend rewrite). */
export const addressFromContact = (
  contact: ContactPersonSchema | null | undefined,
): Partial<ShippingAddress> =>
  contact
    ? {
        name: contactFullName(contact),
        state: contact.state ?? 'CZ',
        city: contact.city ?? '',
        street: contact.street ?? '',
        postal_code: contact.postal_code ?? '',
        email: contact.email ?? '',
        phone: contact.phone ?? '',
      }
    : {}

export const shippingFormFromShipping = (shipping: OutboundOrderShippingSchema): ShippingForm => ({
  shipping_type: shipping.shipping_type,
  package_number: shipping.package_number ?? '',
  width: shipping.width ?? null,
  height: shipping.height ?? null,
  depth: shipping.depth ?? null,
  name: shipping.name ?? '',
  state: shipping.state || 'CZ',
  city: shipping.city ?? '',
  street: shipping.street ?? '',
  postal_code: shipping.postal_code ?? '',
  email: shipping.email ?? '',
  phone: shipping.phone ?? '',
  price: shipping.price ?? null,
  price_with_vat: shipping.price_with_vat ?? null,
})

/** Form of an order that has no shipping yet: only the address is prefilled. */
export const shippingFormFromContact = (
  contact: ContactPersonSchema | null | undefined,
): ShippingForm => ({ ...emptyShippingForm(), ...addressFromContact(contact) })

// q-input may hand over '' (cleared) or a numeric string
const toNumberOrNull = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/** `null` when the (required) shipping type is missing. */
export const toShippingUpsertBody = (
  form: ShippingForm,
): OutboundOrderShippingUpsertSchema | null => {
  if (!form.shipping_type) {
    return null
  }
  const { shipping_type, ...rest } = form
  return {
    ...rest,
    width: toNumberOrNull(rest.width),
    height: toNumberOrNull(rest.height),
    depth: toNumberOrNull(rest.depth),
    price: toNumberOrNull(rest.price),
    price_with_vat: toNumberOrNull(rest.price_with_vat),
    shipping_type_id: shipping_type.id,
  }
}
