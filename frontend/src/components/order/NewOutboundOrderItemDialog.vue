<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat položku</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <ProductAvailability v-if="product" :product-code="product.code" class="w-fit mb-3" />
        <q-form class="flex flex-col gap-2" @submit="addItem">
          <ProductSearchSelect v-model="product" />
          <q-input
            v-model.number="item.amount"
            outlined
            label="Počet"
            hint="Počet Kusů dle MJ"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max9999]"
            @update:model-value="recalcTotal"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model.number="item.unit_price"
            outlined
            label="Prodejní cena"
            hint="Prodejní cena za MJ"
            inputmode="numeric"
            @update:model-value="recalcTotal"
          >
            <template #append>
              <span class="text-sm">{{ currency }} / {{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model.number="item.total_price"
            outlined
            label="Celková cena"
            hint="Celková cena položky"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max99999]"
          >
            <template #append>
              <span class="text-sm">{{ currency }}</span>
            </template>
          </q-input>
          <q-btn type="submit" unelevated color="primary" label="přidat" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { OutboundOrderItemCreateSchema, ProductSchema } from '@/client'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'
import ProductAvailability from '../product/ProductAvailability.vue'

const showDialog = defineModel('show', { default: false })

export interface NewOutboundOrderItemDialogExpose {
  reset: () => void
}

defineProps<{
  currency: string
}>()

const productUom = ref('')

const item = ref<OutboundOrderItemCreateSchema>({
  product_code: '',
  product_name: '',
  amount: 0,
  total_price: 0,
  unit_price: 0,
})

const product = ref<ProductSchema>()

watch(product, (newValue: ProductSchema | undefined) => {
  if (newValue) {
    item.value.product_code = newValue.code
    item.value.product_name = newValue.name
    item.value.unit_price = newValue.purchase_price ?? 0
    item.value.total_price = (newValue.purchase_price ?? 0) * item.value.amount
    productUom.value = newValue.unit
  } else {
    item.value.product_code = ''
    item.value.product_name = ''
  }
})

const recalcTotal = () => {
  item.value.total_price = (item.value.unit_price ?? 0) * item.value.amount
}

const emit = defineEmits<{
  (e: 'addItem', item: OutboundOrderItemCreateSchema): void
}>()

const addItem = () => {
  emit('addItem', item.value)
}

const reset = () => {
  item.value = {
    product_code: '',
    product_name: '',
    amount: 0,
    total_price: 0,
    unit_price: 0,
  }
  product.value = undefined
  showDialog.value = false
}

defineExpose<NewOutboundOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
