<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-4xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.code" outlined label="Kód" :rules="[rules.notEmpty]" />
            <q-input v-model.trim="form.name" outlined label="Název" :rules="[rules.notEmpty]" />
            <q-select
              v-model="form.customer_type"
              :options="customerTypeOptions"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              outlined
              label="Typ"
              :rules="[rules.notEmpty]"
            />
            <q-select
              v-model="form.price_type"
              :options="priceTypeOptions"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              outlined
              label="Cenový typ"
              :rules="[rules.notEmpty]"
            />
          </div>

          <!-- Tax Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.identification" outlined label="IČ" />
            <q-input v-model.trim="form.tax_identification" outlined label="DIČ" />
          </div>

          <!-- Address -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.street" outlined label="Ulice" class="col-span-2" />
            <q-input v-model.trim="form.city" outlined label="Město" />
            <q-input v-model.trim="form.postal_code" outlined label="PSČ" />
          </div>

          <!-- Contact Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.email" outlined label="Email" type="email" />
            <q-input v-model.trim="form.phone" outlined label="Telefon" />
          </div>

          <!-- Business Settings -->
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="form.invoice_due_days"
              outlined
              label="Splatnost (dny)"
              type="number"
            />
            <q-input
              v-model.number="form.block_after_due_days"
              outlined
              label="Blokovat po dnech"
              type="number"
            />
            <InvoicePaymentMethodSelect
              v-model="form.default_payment_method_name"
              label="Výchozí platební metoda"
              hint="Použije se jako předvyplněná metoda při tvorbě faktury."
            />
            <q-checkbox v-model="form.is_self" label="Naše firma (dodavatel na faktuře)" />
          </div>

          <!-- Relationships -->
          <div class="grid grid-cols-2 gap-2">
            <q-select
              v-model="form.customer_group_code"
              :options="customerGroups"
              option-label="name"
              option-value="code"
              emit-value
              map-options
              outlined
              label="Skupina"
              :rules="[rules.notEmpty]"
            />
          </div>

          <!-- Agreements -->
          <div class="flex gap-4">
            <q-checkbox v-model="form.data_collection_agreement" label="GDPR - Sběr dat" />
            <q-checkbox
              v-model="form.marketing_data_use_agreement"
              label="Marketing - Použití dat"
            />
          </div>

          <!-- Status -->
          <div class="flex gap-4">
            <q-checkbox v-model="form.is_valid" label="Platný" />
            <q-checkbox v-model="form.is_deleted" label="Smazaný" />
          </div>

          <!-- Note -->
          <q-input v-model.trim="form.note" outlined type="textarea" rows="3" label="Poznámka" />

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
import type { CustomerCreateOrUpdateSchema, CustomerGroupSchema } from '@/client'
import InvoicePaymentMethodSelect from '@/components/selects/InvoicePaymentMethodSelect.vue'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<CustomerCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
    customerGroups?: CustomerGroupSchema[]
  }>(),
  {
    title: 'Zákazník',
    submitLabel: 'uložit',
    loading: false,
    customerGroups: () => [],
  },
)

const customerTypeOptions = [
  { label: 'Firma', value: 'FIRMA' },
  { label: 'Osoba', value: 'OSOBA' },
]

const priceTypeOptions = [{ label: 'Firmy', value: 'FIRMY' }]

const emit = defineEmits<{
  (e: 'submit', body: CustomerCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
