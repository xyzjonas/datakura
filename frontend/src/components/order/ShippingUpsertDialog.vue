<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-3xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <ShippingTypeSelect v-model="form.shipping_type" required />
            <q-input v-model.trim="form.package_number" outlined label="Číslo balíku" />
          </div>

          <div class="text-xs text-muted uppercase">Rozměry a váha</div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <q-input
              v-model.number="form.width"
              outlined
              type="number"
              min="0"
              step="any"
              label="Šířka"
              suffix="cm"
              :rules="[nonNegative]"
            />
            <q-input
              v-model.number="form.height"
              outlined
              type="number"
              min="0"
              step="any"
              label="Výška"
              suffix="cm"
              :rules="[nonNegative]"
            />
            <q-input
              v-model.number="form.depth"
              outlined
              type="number"
              min="0"
              step="any"
              label="Hloubka"
              suffix="cm"
              :rules="[nonNegative]"
            />
            <q-input
              :model-value="formattedWeight"
              outlined
              readonly
              label="Váha"
              suffix="g"
              hint="Dle položek objednávky"
              data-testid="shipping-weight"
            />
          </div>

          <div class="flex items-center justify-between">
            <span class="text-xs text-muted uppercase">Adresa</span>
            <q-btn
              v-if="contact"
              flat
              dense
              no-caps
              color="primary"
              icon="sym_o_contact_page"
              label="načíst z kontaktu"
              data-testid="shipping-load-contact"
              @click="loadFromContact"
            />
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <q-input v-model.trim="form.name" outlined label="Jméno / Název" />
            <q-select
              v-model="form.state"
              outlined
              label="Stát"
              :options="SHIPPING_STATES"
              emit-value
            />
            <q-input v-model.trim="form.street" outlined label="Ulice" />
            <q-input v-model.trim="form.city" outlined label="Město" />
            <q-input v-model.trim="form.postal_code" outlined label="PSČ" />
            <q-input v-model.trim="form.email" outlined type="email" label="Email" />
            <q-input v-model.trim="form.phone" outlined label="Telefon" />
          </div>

          <div class="text-xs text-muted uppercase">Cena</div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <q-input
              v-model.number="form.price"
              outlined
              type="number"
              min="0"
              step="any"
              label="Cena"
              :suffix="currency"
              :rules="[nonNegative]"
            />
            <q-input
              v-model.number="form.price_with_vat"
              outlined
              type="number"
              min="0"
              step="any"
              label="Cena s DPH"
              :suffix="currency"
              :rules="[nonNegative]"
            />
          </div>

          <div class="mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { ContactPersonSchema, OutboundOrderShippingUpsertSchema } from '@/client'
import ShippingTypeSelect from '@/components/selects/ShippingTypeSelect.vue'
import {
  SHIPPING_STATES,
  addressFromContact,
  toShippingUpsertBody,
  type ShippingForm,
} from '@/utils/shipping-form'
import { computed } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<ShippingForm>({ required: true })

const props = withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
    /** derived from the order, never editable */
    weight?: number
    currency?: string
    /** the order's contact, source of the address */
    contact?: ContactPersonSchema | null
  }>(),
  {
    title: 'Doprava',
    submitLabel: 'uložit',
    loading: false,
    weight: 0,
    currency: undefined,
    contact: null,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: OutboundOrderShippingUpsertSchema): void
}>()

const formattedWeight = computed(() => (Math.round(props.weight * 100) / 100).toFixed(2))

const nonNegative = (val: number | string | null) =>
  val === null || val === '' || Number(val) >= 0 || 'Pole musí být číslo větší nebo rovno 0'

const loadFromContact = () => {
  form.value = { ...form.value, ...addressFromContact(props.contact) }
}

const onSubmit = () => {
  const body = toShippingUpsertBody(form.value)
  if (body) {
    emit('submit', body)
  }
}
</script>
