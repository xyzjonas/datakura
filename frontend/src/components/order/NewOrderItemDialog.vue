<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat položku</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <q-form class="flex flex-col gap-2" @submit="addItem">
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->
          <ProductSearchSelect v-model="product" />
          <q-input
            v-model.number="item.amount"
            outlined
            label="Počet"
            hint="Počet Kusů dle MJ"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max9999]"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model.number="item.unit_price"
            outlined
            label="Nákupní cena"
            hint="Nákupní cena za MJ"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max9999]"
          >
            <template #append>
              <span class="text-sm">{{ currency }} / {{ productUom }}</span>
            </template>
          </q-input>
          <q-btn type="submit" unelevated color="primary" label="přidat" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { InboundOrderItemCreateSchema, ProductSchema } from '@/client'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'

const showDialog = defineModel('show', { default: false })

export interface NewOrderItemDialogExpose {
  reset: () => void
}

defineProps<{
  currency: string
}>()

// just for display purposes
const productUom = ref('')

const item = ref<InboundOrderItemCreateSchema>({
  product_code: '',
  product_name: '',
  amount: 0,
  unit_price: 0,
})

const product = ref<ProductSchema>()

watch(product, (newValue: ProductSchema | undefined) => {
  console.info(`New prod: ${newValue}`)
  if (newValue) {
    item.value.product_code = newValue.code
    item.value.product_name = newValue.name
    item.value.unit_price = newValue.purchase_price ?? 0
    productUom.value = newValue.unit
  } else {
    item.value.product_code = ''
    item.value.product_name = ''
  }
})

const emit = defineEmits<{
  (e: 'addItem', item: InboundOrderItemCreateSchema): void
}>()

const addItem = () => {
  emit('addItem', item.value)
}

const reset = () => {
  item.value = {
    product_code: '',
    product_name: '',
    amount: 0,
    unit_price: 0,
  }
  product.value = undefined
  showDialog.value = false
}

defineExpose<NewOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
