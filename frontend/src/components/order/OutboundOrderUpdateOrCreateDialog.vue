<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center mb-3 gap-2">
          <CurrencyDropdown v-model="item.currency" />
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <q-form class="flex flex-col gap-2" @submit="addItem">
          <CustomerSearchSelect
            v-model="customer"
            hint="Vyhledat subjekt podle názvu, kódu, IČO nebo DIČ."
          />
          <q-input
            v-model.trim="item.external_code"
            outlined
            label="Externí číslo"
            hint="Externí číslo (volitelné)"
          />
          <q-input
            v-model.trim="item.description"
            outlined
            label="Popis"
            hint="Popis (volitelné)"
            autogrow
          ></q-input>
          <q-date
            v-model="deliveryDate"
            landscape
            title="Dodání"
            subtitle="Požadovaný termín"
            class="w-full"
          />
          <q-input
            v-model.trim="item.note"
            outlined
            label="Poznámka"
            hint="Poznámka (volitelné)"
            type="textarea"
          ></q-input>

          <q-btn
            type="submit"
            unelevated
            color="primary"
            :label="submitLabel"
            class="h-[3rem] mt-3"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type {
  CustomerSchema,
  OutboundOrderCreateOrUpdateSchema,
  OutboundOrderSchema,
} from '@/client'
import { ref, watch } from 'vue'
import CurrencyDropdown from './CurrencyDropdown.vue'
import CustomerSearchSelect from '../selects/CustomerSearchSelect.vue'

type Props = {
  title?: string
  submitLabel?: string
  orderOut?: OutboundOrderSchema
}

const deliveryDate = ref<string>('')

const showDialog = defineModel('show', { default: false })
const props = withDefaults(defineProps<Props>(), {
  title: 'Nová objednávka',
  submitLabel: 'vytvořit',
})

export interface OutboundOrderDialogExpose {
  reset: () => void
}

const customer = ref<CustomerSchema>()

const propToRef = (order?: OutboundOrderSchema) => {
  if (!order) {
    return
  }

  customer.value = order.customer
  if (order.requested_delivery_date) {
    deliveryDate.value = new Date(order.requested_delivery_date).toISOString()
  }
  return {
    currency: order.currency,
    note: order.note,
    description: order.description,
    customer_code: order.customer.code,
    customer_name: order.customer.name,
    external_code: order.external_code,
    requested_delivery_date: order.requested_delivery_date,
  } as OutboundOrderCreateOrUpdateSchema
}

const item = ref<OutboundOrderCreateOrUpdateSchema>(
  propToRef(props.orderOut) ?? {
    customer_code: '',
    customer_name: '',
    currency: 'CZK',
    description: '',
    external_code: '',
    note: '',
  },
)

watch(customer, (newValue: CustomerSchema | undefined) => {
  if (newValue) {
    item.value.customer_code = newValue.code
    item.value.customer_name = newValue.name
  } else {
    item.value.customer_code = ''
    item.value.customer_name = ''
  }
})

watch(deliveryDate, (newValue: string) => {
  item.value.requested_delivery_date = new Date(newValue).toISOString()
})

const emit = defineEmits<{
  (e: 'createOrder', item: OutboundOrderCreateOrUpdateSchema): void
}>()

const addItem = () => {
  emit('createOrder', item.value)
}

const reset = () => {
  item.value = {
    customer_code: '',
    customer_name: '',
    currency: 'CZK',
    description: '',
    external_code: '',
    note: '',
  }
  customer.value = undefined
  showDialog.value = false
}

defineExpose<OutboundOrderDialogExpose>({
  reset,
})
</script>
