<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-3xl rounded-t-6">
      <div class="flex flex-col gap-5 p-4 md:p-6">
        <div class="flex items-start gap-4 flex-nowrap">
          <div>
            <span class="text-2xl uppercase">Vytvořit fakturu</span>
            <div class="mt-2 text-sm text-muted">
              Vybrané objednávky spojíme do jednoho systémově generovaného dokladu.
            </div>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <ForegroundPanel>
          <div class="text-xs font-bold uppercase text-muted">Odberatel</div>
          <div class="mt-2 text-xl font-semibold text-primary">
            {{ customerName }}
          </div>
          <div class="mt-2 text-sm text-muted">
            {{ selectedOrders.length }} objednávek, měna {{ currencyLabel }}
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <q-chip
              v-for="order in selectedOrders"
              :key="order.code"
              dense
              square
              outline
              class="text-primary"
            >
              {{ order.code }}
            </q-chip>
          </div>
        </ForegroundPanel>

        <ForegroundPanel>
          <div class="text-xs font-bold uppercase tracking-[0.18em] text-muted">
            Automatické číslo
          </div>
          <div class="mt-2 text-lg font-semibold">Vygeneruje backend</div>
          <div class="mt-2 text-sm text-muted">
            Systém přiřadí unikátní číslo faktury při potvrzení.
          </div>
        </ForegroundPanel>

        <q-form class="grid gap-3 md:grid-cols-2" @submit="onSubmit">
          <q-input
            v-model="form.issued_date"
            outlined
            label="Datum vystaveni"
            type="date"
            :rules="[rules.notEmpty]"
          />
          <q-input
            v-model="form.taxable_supply_date"
            outlined
            label="Datum zdanitelného plnění"
            type="date"
            :rules="[rules.notEmpty]"
          />
          <q-input
            v-model="form.due_date"
            outlined
            label="Splatnost"
            type="date"
            :rules="[rules.notEmpty]"
          />
          <InvoicePaymentMethodSelect
            v-model="form.payment_method_name"
            label="Platební metoda"
            :hint="paymentMethodHint"
            :placeholder="defaultPaymentMethodName || 'Vyberte platební metodu'"
            :rules="[rules.notEmpty]"
          />
          <q-input
            :model-value="supplierName"
            outlined
            label="Dodavatel"
            hint="Naše firma, doplněno automaticky."
            readonly
          />
          <q-input v-model="form.external_code" outlined label="Externí číslo (volitelné)" />
          <q-input v-model="form.paid_date" outlined label="Datum úhrady (volitelné)" type="date" />
          <q-input
            v-model="form.note"
            outlined
            autogrow
            label="Poznámka (volitelné)"
            class="md:col-span-2"
          />

          <div class="mt-2 flex justify-end gap-2 md:col-span-2">
            <q-btn flat color="primary" label="Zrušit" v-close-popup />
            <q-btn
              type="submit"
              unelevated
              color="positive"
              :loading="loading"
              label="Vytvořit fakturu"
              class="min-w-[12rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { CustomerSchema, OutboundInvoiceCreateSchema, OutboundOrderSchema } from '@/client'
import InvoicePaymentMethodSelect from '@/components/selects/InvoicePaymentMethodSelect.vue'
import { rules } from '@/utils/rules'
import { computed, ref, watch } from 'vue'
import { createDefaultOutboundInvoiceForm } from './outbound-invoice'
import ForegroundPanel from '../ForegroundPanel.vue'

const showDialog = defineModel<boolean>('show', { default: false })

const props = withDefaults(
  defineProps<{
    selectedOrders?: OutboundOrderSchema[]
    selfSupplier?: CustomerSchema | null
    loading?: boolean
  }>(),
  {
    selectedOrders: () => [],
    selfSupplier: null,
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', payload: OutboundInvoiceCreateSchema): void
}>()

const form = ref<OutboundInvoiceCreateSchema>(
  createDefaultOutboundInvoiceForm(props.selectedOrders),
)

const customerName = computed(() => props.selectedOrders[0]?.customer.name ?? 'Bez odberatele')
const supplierName = computed(() => props.selfSupplier?.name ?? '')
const currencyLabel = computed(() => props.selectedOrders[0]?.currency ?? '-')
const defaultPaymentMethodName = computed(
  () => props.selectedOrders[0]?.customer.default_payment_method?.name ?? '',
)
const paymentMethodHint = computed(() =>
  defaultPaymentMethodName.value
    ? `Predvyplneno z odberatele: ${defaultPaymentMethodName.value}`
    : 'Zpusob uhrady pro vygenerovanou fakturu.',
)

const resetForm = () => {
  form.value = createDefaultOutboundInvoiceForm(props.selectedOrders)
}

watch(
  () => [showDialog.value, props.selectedOrders],
  ([isOpen]) => {
    if (!isOpen) {
      return
    }

    resetForm()
  },
  { deep: true },
)

const onSubmit = () => {
  emit('submit', {
    ...form.value,
    order_codes: props.selectedOrders.map((order) => order.code),
  })
}
</script>
