<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-2xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <q-input
            v-model.trim="form.code"
            outlined
            label="Číslo faktury"
            hint="Interní číslo faktury podle dokladu od dodavatele."
            :rules="[rules.notEmpty]"
          />

          <q-file
            v-model="invoiceFile"
            outlined
            accept=".pdf,application/pdf"
            label="PDF faktury"
            :hint="
              existingDocument
                ? `Nahrejte nový soubor, který nahradí stávající soubor \'${existingDocument.name}\''`
                : 'Nahrajte originální PDF doklad k této faktuře.'
            "
            :rules="props.requireInvoiceFile ? [invoiceFileRule] : []"
            clearable
          />

          <q-btn
            flat
            no-caps
            color="primary"
            class="self-start"
            :icon="showOptional ? 'expand_less' : 'expand_more'"
            :label="showOptional ? 'Skrýt další údaje' : 'Další údaje (volitelné)'"
            data-testid="invoice-optional-toggle"
            @click="showOptional = !showOptional"
          />

          <q-slide-transition>
            <div v-show="showOptional" class="flex flex-col gap-3" data-testid="invoice-optional">
              <q-select
                v-model="form.currency"
                outlined
                label="Měna"
                hint="Měna, ve které je faktura vystavena."
                :options="currencies"
                emit-value
              />

              <CustomerSearchSelect
                v-model="customer"
                label="Odběratel"
                hint="Odběratel je vždy naše firma."
                :required="false"
                :disable="lockCustomer"
              />
              <CustomerSearchSelect
                v-model="supplier"
                label="Dodavatel"
                hint="Vyberte dodavatele, který fakturu vystavil."
                :required="false"
              />

              <q-input
                v-model="form.issued_date"
                outlined
                label="Datum vystavení"
                hint="Datum uvedené na faktuře jako datum vystavení."
                type="date"
              />
              <q-input
                v-model="form.taxable_supply_date"
                outlined
                label="Datum zdanitelného plnění"
                hint="Datum, ke kterému vznikla daňová povinnost."
                type="date"
              />
              <q-input
                v-model="form.due_date"
                outlined
                label="Splatnost"
                hint="Termín, do kdy má být faktura uhrazena."
                type="date"
              />

              <InvoicePaymentMethodSelect
                v-model="form.payment_method_name"
                label="Platební metoda"
                hint="Zvolte způsob úhrady uvedený na faktuře."
              />

              <q-input
                v-model="form.paid_date"
                outlined
                label="Datum úhrady"
                hint="Vyplňte pouze pokud je faktura již zaplacena."
                type="date"
              />

              <q-input
                v-model.trim="form.external_code"
                outlined
                label="Číslo objednávky zákazníka"
                hint="Číslo faktury v systému partnera."
              />
              <q-input
                v-model.trim="form.note"
                outlined
                label="Poznámka"
                hint="Doplňující informace k faktuře."
              />
            </div>
          </q-slide-transition>

          <div class="mt-4 flex justify-end gap-2">
            <q-btn flat color="primary" label="Zrušit" v-close-popup />
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { CustomerBaseSchema, InvoiceStoreSchema, MediaFileSchema } from '@/client'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'
import CustomerSearchSelect from '../selects/CustomerSearchSelect.vue'
import InvoicePaymentMethodSelect from '../selects/InvoicePaymentMethodSelect.vue'
import type { InvoiceUpsertSubmitPayload } from './invoice-upload'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<InvoiceStoreSchema>({ required: true })

const props = withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
    defaultCustomer?: CustomerBaseSchema | null
    defaultSupplier?: CustomerBaseSchema | null
    lockCustomer?: boolean
    requireInvoiceFile?: boolean
    existingDocument?: MediaFileSchema | null
  }>(),
  {
    title: 'Nová faktura',
    submitLabel: 'vytvořit',
    loading: false,
    defaultCustomer: null,
    defaultSupplier: null,
    lockCustomer: false,
    requireInvoiceFile: true,
  },
)

const emit = defineEmits<{
  (e: 'submit', payload: InvoiceUpsertSubmitPayload): void
}>()

const customer = ref<CustomerBaseSchema | undefined>()
const supplier = ref<CustomerBaseSchema | undefined>()
const invoiceFile = ref<File | null>(null)
const showOptional = ref(false)
const currencies = ['CZK', 'EUR', 'PLN']

const invoiceFileRule = (val: File | null) => !!val || 'Nahrajte PDF faktury.'

const syncPaymentMethodFromCustomer = (selectedCustomer?: CustomerBaseSchema) => {
  if (form.value.payment_method_name) {
    return
  }

  form.value.payment_method_name = selectedCustomer?.default_payment_method?.name ?? ''
}

watch(
  () => showDialog.value,
  (isOpen) => {
    if (!isOpen) {
      return
    }
    invoiceFile.value = null
    showOptional.value = false
    customer.value = props.defaultCustomer ?? undefined
    supplier.value = props.defaultSupplier ?? undefined
    syncPaymentMethodFromCustomer(customer.value)
  },
  { immediate: true },
)

watch(customer, (selectedCustomer) => {
  syncPaymentMethodFromCustomer(selectedCustomer)
})

const onSubmit = () => {
  const body: InvoiceStoreSchema = {
    ...form.value,
    issued_date: form.value.issued_date || undefined,
    due_date: form.value.due_date || undefined,
    taxable_supply_date: form.value.taxable_supply_date || undefined,
    paid_date: form.value.paid_date || undefined,
    payment_method_name: form.value.payment_method_name || undefined,
    currency: form.value.currency || 'CZK',
    customer_code: customer.value?.code,
    supplier_code: supplier.value?.code,
  }
  emit('submit', {
    body,
    invoiceFile: invoiceFile.value,
  })
}
</script>
