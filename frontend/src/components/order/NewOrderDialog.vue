<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center mb-3 gap-2">
          <CurrencyDropdown v-model="item.currency" />
          <span class="text-2xl uppercase">Nová objednávka</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <q-form class="flex flex-col gap-2" @submit="addItem">
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->
          <CustomerSearchSelect v-model="customer" />
          <q-input
            v-model="item.external_code"
            outlined
            label="Externí číslo"
            hint="Externí číslo (volitelné)"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model="item.description"
            outlined
            label="Popis"
            hint="Popis (volitelné)"
          ></q-input>
          <q-input
            v-model="item.note"
            outlined
            label="Poznámka"
            hint="Poznámka (volitelné)"
          ></q-input>

          <q-btn type="submit" unelevated color="primary" label="vytvořit" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { CustomerSchema, IncomingOrderCreateOrUpdateSchema } from '@/client'
import { ref, watch } from 'vue'
import CustomerSearchSelect from '../product/CustomerSearchSelect.vue'
import CurrencyDropdown from './CurrencyDropdown.vue'

const showDialog = defineModel('show', { default: false })

export interface NewOrderDialogExpose {
  reset: () => void
}

// just for display purposes
const productUom = ref('')

const item = ref<IncomingOrderCreateOrUpdateSchema>({
  supplier_code: '',
  supplier_name: '',
  currency: 'CZK',
  description: '',
  external_code: '',
  note: '',
})

const customer = ref<CustomerSchema>()

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
  (e: 'createOrder', item: IncomingOrderCreateOrUpdateSchema): void
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
