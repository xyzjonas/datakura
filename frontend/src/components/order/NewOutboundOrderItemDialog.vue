<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat položku</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <ProductAvailability v-if="product" :product-code="product.code" class="w-fit mb-3" />
        <q-form ref="form" class="flex flex-col gap-2" @submit="addItem">
          <ProductSearchSelect ref="productSelect" v-model="product" />
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
            :base-currency="baseCurrency"
            :exchange-rate="exchangeRate"
            :unit="productUom"
            :base-price="pricingContext.basePrice"
            :suggested-price="pricingContext.suggestedPrice"
            :avg-purchase-price="pricingContext.avgPurchasePrice"
            :discount-percent="pricingContext.discountPercent"
            :reason="pricingContext.reason"
            :price-source="pricingContext.source"
            @update:model-value="recalcTotalFromUnit"
          />
          <q-input
            v-model.number="item.total_price"
            outlined
            label="Celková cena"
            :hint="totalHint"
            inputmode="numeric"
            :rules="[rules.atLeastOne, rules.max99999]"
            @update:model-value="recalcUnitFromTotal"
          >
            <template #append>
              <span class="text-sm">{{ currency }}</span>
            </template>
          </q-input>
          <ItemMarginSummary
            v-if="product"
            :currency="baseCurrency"
            :amount="item.amount"
            :purchase-price="baseAvgPurchasePrice"
            :total-price="toBase(item.total_price ?? 0, exchangeRate)"
          />
          <CustomerProductCodeInput
            v-if="requiresOwnCodes"
            v-model="item.customer_product_code"
            required
          />
          <OutboundItemRequirements
            v-model:package-type-name="item.desired_package_type_name"
            v-model:batch-code="item.desired_batch_code"
            v-model:batch-certification="batchCertification"
            v-model:origin-country="item.required_origin_country"
            :product-name="item.product_name"
            :product-code="item.product_code"
          />
          <div class="flex flex-col gap-2">
            <q-btn
              flat
              dense
              no-caps
              :icon="showNote ? 'expand_less' : 'expand_more'"
              :label="showNote ? 'Skrýt poznámku' : 'Přidat poznámku'"
              class="self-start text-muted"
              @click="toggleNote"
            />
            <q-input
              v-if="showNote"
              v-model.trim="item.note"
              outlined
              label="Poznámka"
              type="textarea"
              autogrow
            />
          </div>
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
import {
  warehouseApiRoutesProductGetProductCustomerCodes,
  warehouseApiRoutesProductGetProductSellingPrice,
  type OutboundOrderItemCreateSchema,
  type ProductSchema,
  type SellingPriceLookupSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { fromBase, toBase } from '@/utils/currency'
import { round } from '@/utils/round'
import { rules } from '@/utils/rules'
import { computed, nextTick, ref, watch } from 'vue'
import type { QForm } from 'quasar'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import CustomerProductCodeInput from './CustomerProductCodeInput.vue'
import ItemMarginSummary from './ItemMarginSummary.vue'
import OutboundItemRequirements from './OutboundItemRequirements.vue'
import SellingPriceEditor from './SellingPriceEditor.vue'

const showDialog = defineModel('show', { default: false })
const { onResponse } = useApi()

export interface NewOutboundOrderItemDialogExpose {
  reset: (close?: boolean) => void
}

const props = defineProps<{
  /** Document currency: the prices are entered in it. */
  currency: string
  baseCurrency: string
  /** Base currency units per 1 unit of the document currency. */
  exchangeRate: number
  customerCode: string
  /** Customer orders by own codes - the code field is shown (and highlighted when empty). */
  requiresOwnCodes?: boolean
}>()

const productUom = ref('')
const pricingLookup = ref<SellingPriceLookupSchema>()
const showNote = ref(false)

/** Certification of the chosen batch - display only (the server derives it from the batch). */
const batchCertification = ref<{ id?: number; code: string } | null>(null)

const item = ref<OutboundOrderItemCreateSchema>({
  product_code: '',
  product_name: '',
  amount: 0,
  total_price: 0,
  unit_price: 0,
  desired_package_type_name: null,
  desired_batch_code: null,
  required_origin_country: null,
  note: null,
  customer_product_code: null,
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
      item.value.unit_price = toDocument(data.data.final_price)
    } else {
      pricingLookup.value = undefined
      item.value.unit_price = toDocument(newValue.base_price ?? 0)
    }
    item.value.total_price = (item.value.unit_price ?? 0) * item.value.amount
  }

  // prefill the code the customer already uses for this product
  const resolveOwnCode = async () => {
    item.value.customer_product_code = null
    if (!newValue || !props.requiresOwnCodes) {
      return
    }
    const response = await warehouseApiRoutesProductGetProductCustomerCodes({
      path: { product_code: newValue.code },
    })
    const entries = onResponse(response)?.data ?? []
    const own = entries.find((entry) => entry.customer.code === props.customerCode)
    if (own && product.value?.code === newValue.code) {
      item.value.customer_product_code = own.code
    }
  }

  void resolvePricing()
  void resolveOwnCode()
})

const foreign = computed(() => props.currency !== props.baseCurrency)

/** Prices of the system are in the base currency, the form is in the document one. */
const toDocument = (basePrice: number) =>
  foreign.value ? round(fromBase(basePrice, props.exchangeRate)) : basePrice

const totalHint = computed(() =>
  foreign.value
    ? `Celková cena položky ≈ ${toBase(item.value.total_price ?? 0, props.exchangeRate).toFixed(2)} ${props.baseCurrency}`
    : 'Celková cena položky',
)

const baseAvgPurchasePrice = computed(() => product.value?.purchase_price ?? 0)

const pricingContext = computed(() => ({
  basePrice: toDocument(pricingLookup.value?.base_price ?? product.value?.base_price ?? 0),
  suggestedPrice: toDocument(pricingLookup.value?.final_price ?? product.value?.base_price ?? 0),
  avgPurchasePrice: toDocument(baseAvgPurchasePrice.value),
  discountPercent: pricingLookup.value?.discount_percent ?? 0,
  reason: pricingLookup.value?.reason ?? 'Base selling price',
  source: pricingLookup.value?.source ?? 'BASE_PRICE',
}))

const recalcTotalFromUnit = () => {
  item.value.total_price = (item.value.unit_price ?? 0) * item.value.amount
}

const recalcUnitFromTotal = () => {
  if (!item.value.amount) {
    item.value.unit_price = 0
    return
  }
  item.value.unit_price = (item.value.total_price ?? 0) / item.value.amount
}

const emit = defineEmits<{
  (e: 'addItem', item: OutboundOrderItemCreateSchema, keepOpen: boolean): void
}>()

const toggleNote = () => {
  showNote.value = !showNote.value
  if (!showNote.value) {
    item.value.note = null
  }
}

const form = ref<QForm>()
const productSelect = ref<InstanceType<typeof ProductSearchSelect>>()
const keepOpen = ref(false)

const addItem = () => {
  // a price entered in a foreign currency is stored as it is, the base one is derived from it
  const payload: OutboundOrderItemCreateSchema = foreign.value
    ? { ...item.value, total_price: null, document_total_price: item.value.total_price }
    : item.value
  emit('addItem', payload, keepOpen.value)
  keepOpen.value = false
}

const reset = (close = true) => {
  batchCertification.value = null
  item.value = {
    product_code: '',
    product_name: '',
    amount: 0,
    total_price: 0,
    unit_price: 0,
    desired_package_type_name: null,
    desired_batch_code: null,
    required_origin_country: null,
    note: null,
    customer_product_code: null,
  }
  showNote.value = false
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

defineExpose<NewOutboundOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
