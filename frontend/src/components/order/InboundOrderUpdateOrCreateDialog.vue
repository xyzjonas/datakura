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
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->
          <CustomerSearchSelect v-model="customer" />
          <q-input
            v-model.trim="item.external_code"
            outlined
            label="Externí číslo"
            hint="Externí číslo (volitelné)"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model.trim="item.description"
            outlined
            label="Popis"
            hint="Popis (volitelné)"
            autogrow
          ></q-input>
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
import type { CustomerSchema, InboundOrderCreateOrUpdateSchema, InboundOrderSchema } from '@/client'
import { ref, watch } from 'vue'
import CustomerSearchSelect from '../product/CustomerSearchSelect.vue'
import CurrencyDropdown from './CurrencyDropdown.vue'

type Props = {
  title?: string
  submitLabel?: string
  orderIn?: InboundOrderSchema
}

const showDialog = defineModel('show', { default: false })
const props = withDefaults(defineProps<Props>(), {
  title: 'Nová objednávka',
  submitLabel: 'vytvořit',
})

export interface NewOrderDialogExpose {
  reset: () => void
}

// just for display purposes
const productUom = ref('')
const customer = ref<CustomerSchema>()

const propToRef = (order?: InboundOrderSchema) => {
  if (!order) {
    return
  }

  customer.value = order.supplier
  return {
    currency: order.currency,
    note: order.note,
    state: order.state,
    description: order.description,
    supplier_code: order.supplier.code,
    supplier_name: order.supplier.name,
    external_code: order.external_code,
  } as InboundOrderCreateOrUpdateSchema
}

const item = ref<InboundOrderCreateOrUpdateSchema>(
  propToRef(props.orderIn) ?? {
    supplier_code: '',
    supplier_name: '',
    currency: 'CZK',
    description: '',
    external_code: '',
    note: '',
  },
)

watch(customer, (newValue: CustomerSchema | undefined) => {
  if (newValue) {
    item.value.supplier_code = newValue.code
    item.value.supplier_name = newValue.name
  } else {
    item.value.supplier_code = ''
    item.value.supplier_name = ''
  }
})

const emit = defineEmits<{
  (e: 'createOrder', item: InboundOrderCreateOrUpdateSchema): void
}>()

const addItem = () => {
  emit('createOrder', item.value)
}

const reset = () => {
  item.value = {
    supplier_code: '',
    supplier_name: '',
    currency: 'CZK',
    description: '',
    external_code: '',
    note: '',
  }
  customer.value = undefined
  showDialog.value = false
}

defineExpose<NewOrderDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
