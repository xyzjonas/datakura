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
            @update:model-value="recalcTotalFromUnit"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <SellingPriceEditor
            v-model="item.unit_price"
            :currency="currency"
            :unit="productUom"
            :base-price="pricingContext.basePrice"
            :suggested-price="pricingContext.suggestedPrice"
            :avg-purchase-price="pricingContext.avgPurchasePrice"
            :discount-percent="pricingContext.discountPercent"
            :reason="pricingContext.reason"
            @update:model-value="recalcTotalFromUnit"
          />
          <q-input
            v-model.number="item.total_price"
            outlined
            label="Celková cena"
            hint="Celková cena položky"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max99999]"
            @update:model-value="recalcUnitFromTotal"
          >
            <template #append>
              <span class="text-sm">{{ currency }}</span>
            </template>
          </q-input>
          <q-input
            v-model="batchCode"
            outlined
            label="Požadovaná šarže"
            hint="Volitelné. Zadejte existující kód šarže."
          />
          <q-btn type="submit" unelevated color="primary" label="přidat" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductGetProductSellingPrice,
  type OutboundOrderItemCreateSchema,
  type ProductSchema,
  type SellingPriceLookupSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { computed, ref, watch } from 'vue'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import SellingPriceEditor from './SellingPriceEditor.vue'

const showDialog = defineModel('show', { default: false })
const { onResponse } = useApi()

export interface NewOutboundOrderItemDialogExpose {
  reset: () => void
}

const props = defineProps<{
  currency: string
  customerCode: string
}>()

const productUom = ref('')
const pricingLookup = ref<SellingPriceLookupSchema>()
const batchCode = ref('')

const item = ref<OutboundOrderItemCreateSchema>({
  product_code: '',
  product_name: '',
  amount: 0,
  total_price: 0,
  unit_price: 0,
  desired_package_type_name: null,
  desired_batch_code: null,
})

const product = ref<ProductSchema>()

watch(product, (newValue: ProductSchema | undefined) => {
  const resolvePricing = async () => {
    if (!newValue) {
      item.value.product_code = ''
      item.value.product_name = ''
      pricingLookup.value = undefined
      return
    }

    item.value.product_code = newValue.code
    item.value.product_name = newValue.name
    productUom.value = newValue.unit

    const response = await warehouseApiRoutesProductGetProductSellingPrice({
      path: { product_code: newValue.code },
      query: { customer_code: props.customerCode },
    })
    const data = onResponse(response)
    if (data?.data) {
      pricingLookup.value = data.data
      item.value.unit_price = data.data.final_price
    } else {
      pricingLookup.value = undefined
      item.value.unit_price = newValue.base_price ?? 0
    }
    item.value.total_price = (item.value.unit_price ?? 0) * item.value.amount
  }

  void resolvePricing()
})

const pricingContext = computed(() => ({
  basePrice: pricingLookup.value?.base_price ?? product.value?.base_price ?? 0,
  suggestedPrice: pricingLookup.value?.final_price ?? product.value?.base_price ?? 0,
  avgPurchasePrice: product.value?.purchase_price ?? 0,
  discountPercent: pricingLookup.value?.discount_percent ?? 0,
  reason: pricingLookup.value?.reason ?? 'Base selling price',
}))

const recalcTotalFromUnit = () => {
  item.value.total_price = (item.value.unit_price ?? 0) * item.value.amount
}

const recalcUnitFromTotal = () => {
  if (!item.value.amount) {
    item.value.unit_price = 0
    return
  }
  item.value.unit_price = item.value.total_price / item.value.amount
}

const emit = defineEmits<{
  (e: 'addItem', item: OutboundOrderItemCreateSchema): void
}>()

const addItem = () => {
  item.value.desired_package_type_name = null
  item.value.desired_batch_code = batchCode.value || null
  emit('addItem', item.value)
}

const reset = () => {
  item.value = {
    product_code: '',
    product_name: '',
    amount: 0,
    total_price: 0,
    unit_price: 0,
    desired_package_type_name: null,
    desired_batch_code: null,
  }
  batchCode.value = ''
  product.value = undefined
  showDialog.value = false
}

defineExpose<NewOutboundOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
