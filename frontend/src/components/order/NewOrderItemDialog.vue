<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat položku</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <ProductAvailability v-if="product" :product-code="product.code" class="w-fit mb-3" />
        <q-form ref="form" class="flex flex-col gap-2" @submit="addItem">
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->
          <ProductSearchSelect ref="productSelect" v-model="product" />
          <q-input
            v-model.number="item.amount"
            outlined
            label="Počet"
            hint="Počet Kusů dle MJ"
            inputmode="numeric"
            :debounce="300"
            :rules="[rules.atLeastOne, rules.max9999]"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <div class="ml-1" v-if="product">
            <small :class="percentDifference >= 0 ? 'text-positive' : 'text-negative'">
              Cena je o
              <strong>{{ Math.abs(percentDifference) }}%</strong>
              {{ percentDifference > 0 ? 'nižší' : 'vyšší' }} než aktuální průměrná nákupní cena ({{
                serverPurchasePrice
              }}
              {{ product?.currency }})</small
            >
          </div>
          <q-input
            :model-value="derivedUnitPrice"
            readonly
            outlined
            label="Nákupní cena"
            hint="Nákupní cena za MJ"
            inputmode="numeric"
            :error="priceSanityCheck"
            :error-message="`Nákupní cena se příliš liší od aktuální ceny produktu (${serverPurchasePrice} ${product?.currency}) o ${percentDifference}%!`"
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
            :rules="[rules.atLeastZero, rules.max99999]"
          >
            <template #append>
              <span class="text-sm">{{ currency }}</span>
            </template>
          </q-input>
          <div class="flex gap-2 mt-3">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              label="přidat"
              class="h-[3rem] flex-1"
              @click="keepOpen = false"
            />
            <q-btn
              type="submit"
              outline
              color="primary"
              label="přidat a nový"
              class="h-[3rem] flex-1"
              @click="keepOpen = true"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { InboundOrderItemCreateSchema, ProductSchema } from '@/client'
import { rules } from '@/utils/rules'
import { computed, nextTick, ref, watch } from 'vue'
import type { QForm } from 'quasar'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import { round } from '@/utils/round'

const showDialog = defineModel('show', { default: false })

export interface NewOrderItemDialogExpose {
  reset: (close?: boolean) => void
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
  total_price: 0,
  unit_price: 0,
})

const allowedPercent = 20
const serverPurchasePrice = ref(0)
const derivedUnitPrice = computed(() => {
  if (!item.value.amount) {
    return serverPurchasePrice.value
  }
  if (!item.value.total_price) {
    return serverPurchasePrice.value
  }
  return round(item.value.total_price / item.value.amount)
})

const percentDifference = computed(() => {
  if (!serverPurchasePrice.value) {
    return 0
  }
  return round((1 - derivedUnitPrice.value / serverPurchasePrice.value) * 100)
})
const priceSanityCheck = computed(() => {
  if (!product.value) {
    return false
  }
  return percentDifference.value > allowedPercent || percentDifference.value < -allowedPercent
})
const product = ref<ProductSchema>()

watch(product, (newValue: ProductSchema | undefined) => {
  console.info(`New prod: ${newValue}`)
  if (newValue) {
    item.value.product_code = newValue.code
    item.value.product_name = newValue.name
    item.value.unit_price = newValue.purchase_price ?? 0
    item.value.total_price = (newValue.purchase_price ?? 0) * item.value.amount
    serverPurchasePrice.value = newValue.purchase_price ?? 0
    productUom.value = newValue.unit
  } else {
    item.value.product_code = ''
    item.value.product_name = ''
  }
})

watch(
  () => item.value.amount,
  (newAmount) => {
    if (item.value.total_price <= 0) {
      item.value.total_price = round((item.value.unit_price ?? 0) * newAmount)
    }
  },
)

const emit = defineEmits<{
  (e: 'addItem', item: InboundOrderItemCreateSchema, keepOpen: boolean): void
}>()

const form = ref<QForm>()
const productSelect = ref<InstanceType<typeof ProductSearchSelect>>()
const keepOpen = ref(false)

const addItem = () => {
  emit('addItem', item.value, keepOpen.value)
  keepOpen.value = false
}

const reset = (close = true) => {
  item.value = {
    product_code: '',
    product_name: '',
    amount: 0,
    total_price: 0,
    unit_price: 0,
  }
  product.value = undefined
  if (close) {
    showDialog.value = false
    return
  }
  nextTick(() => {
    form.value?.resetValidation()
    productSelect.value?.focus()
  })
}

defineExpose<NewOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
