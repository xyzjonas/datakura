<template>
  <div class="flex flex-col xl:flex-row w-full justify-between items-start xl:items-center gap-5">
    <div class="flex items center gap-3">
      <IndexRectangle v-if="displayIndex !== undefined" :index="displayIndex" />
      <div>
        <a
          @click="
            $router.push({
              name: 'productDetail',
              params: { productCode: item.product.code },
            })
          "
          class="link"
          >{{ item.product.name }}</a
        >
        <br />
        <span class="text-xs text-gray-5">{{ item.product.code }}</span>
      </div>
    </div>
    <div
      class="flex flex-col xl:flex-row gap-3 flex-1 items-start xl:items-center justify-start lg:justify-end flex-nowrap min-w-[670px]"
    >
      <ProductAvailability :product-code="item.product.code" class="" />
      <q-input
        v-model.number="item.amount"
        :readonly="readonly"
        dense
        outlined
        class="w-full"
        label="Počet"
        @update:model-value="update('amount')"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ item.product.unit }}</span>
        </template>
      </q-input>
      <q-input
        v-if="props.orderType === 'inbound'"
        v-model.number="unitPrice"
        :readonly="isUnitPriceReadonly"
        dense
        outlined
        class="max-w-50"
        label="Nákupní cena"
        @update:model-value="update('unit')"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ currency }} / {{ item.product.unit }}</span>
        </template>
      </q-input>

      <SellingPriceEditor
        v-else
        v-model="unitPrice"
        :readonly="readonly"
        :currency="currency"
        :unit="item.product.unit"
        :base-price="pricingContext.basePrice"
        :suggested-price="pricingContext.suggestedUnitPrice"
        :avg-purchase-price="pricingContext.avgPurchasePrice"
        :discount-percent="pricingContext.discountPercent"
        :reason="pricingContext.reason"
        :price-source="pricingContext.source"
        :can-persist-override="orderType === 'outbound' && !!customerCode && !readonly"
        :override-saving="isPersistingOverride"
        @update:model-value="update('unit')"
        @persist-override="persistOverrideForCustomer"
      />
      <q-input
        :readonly="readonly"
        v-model.number="totalPrice"
        @update:model-value="update('total')"
        dense
        outlined
        class="max-w-40"
        label="Celková cena"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ currency }}</span>
        </template>
      </q-input>
      <q-btn
        v-if="!readonly"
        icon="sym_o_close_small"
        color="negative"
        flat
        dense
        @click="$emit('dissolveItem')"
      ></q-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder,
  warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder,
  warehouseApiRoutesProductUpsertProductCustomerPriceOverride,
  type CreditNoteSupplierItemSchema,
  type InboundOrderItemSchema,
  type OutboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { round } from '@/utils/round'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'
import IndexRectangle from '../IndexRectangle.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import SellingPriceEditor from './SellingPriceEditor.vue'

const $q = useQuasar()
const { onResponse } = useApi()

const props = defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  orderType: 'inbound' | 'outbound'
  customerCode?: string
}>()
defineEmits<{ (e: 'dissolveItem'): void }>()

const item = defineModel<
  InboundOrderItemSchema | OutboundOrderItemSchema | CreditNoteSupplierItemSchema
>('item', {
  required: true,
})

const totalPrice = ref(round(item.value.unit_price * item.value.amount))
const unitPrice = ref(round(item.value.unit_price))
const computeUnitFromTotal = () => {
  if (!item.value.amount) {
    return 0
  }
  return round(totalPrice.value / item.value.amount)
}

const isUnitPriceReadonly = computed(() => props.readonly || props.orderType === 'inbound')

const displayIndex = computed(() => ('index' in item.value ? item.value.index + 1 : undefined))

type OutboundPricingDetails = {
  base_price?: number
  avg_purchase_price?: number
  suggested_unit_price?: number
  discount_percent?: number
  reason?: string
  source?: string
}

const pricingContext = computed(() => {
  const pricing = (
    item.value as OutboundOrderItemSchema & { pricing_details?: OutboundPricingDetails }
  ).pricing_details
  const basePrice = round(pricing?.base_price ?? item.value.product.base_price ?? unitPrice.value)
  const avgPurchasePrice = round(
    pricing?.avg_purchase_price ?? item.value.product.purchase_price ?? 0,
  )
  const suggestedUnitPrice = round(pricing?.suggested_unit_price ?? basePrice)

  return {
    basePrice,
    avgPurchasePrice,
    suggestedUnitPrice,
    discountPercent: round(pricing?.discount_percent ?? 0),
    reason: pricing?.reason ?? 'Base selling price',
    source: pricing?.source ?? 'BASE_PRICE',
  }
})

const isPersistingOverride = ref(false)

const update = async (changedField: 'amount' | 'unit' | 'total') => {
  if (props.orderType === 'outbound') {
    if (changedField === 'total') {
      unitPrice.value = computeUnitFromTotal()
    } else {
      totalPrice.value = round(item.value.amount * round(unitPrice.value))
    }
  } else {
    unitPrice.value = computeUnitFromTotal()
  }

  const payload = {
    product_code: item.value.product.code,
    product_name: item.value.product.name,
    amount: item.value.amount,
    total_price: totalPrice.value,
    unit_price: unitPrice.value,
  }

  const res =
    props.orderType === 'outbound'
      ? await warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder({
          path: { order_code: props.orderCode },
          body: payload,
        })
      : await warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder({
          path: { order_code: props.orderCode },
          body: payload,
        })

  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
    totalPrice.value = data.data.total_price
    unitPrice.value = data.data.unit_price
    $q.notify({ type: 'positive', message: 'Položka aktualizována' })
  }
}

const persistOverrideForCustomer = async () => {
  if (props.orderType !== 'outbound' || !props.customerCode) {
    return
  }

  isPersistingOverride.value = true
  const response = await warehouseApiRoutesProductUpsertProductCustomerPriceOverride({
    path: { product_code: item.value.product.code },
    body: {
      customer_code: props.customerCode,
      fixed_price: unitPrice.value,
    },
  })
  isPersistingOverride.value = false

  const data = onResponse(response)
  if (!data?.data || props.orderType !== 'outbound') {
    return
  }

  const outboundItem = item.value as OutboundOrderItemSchema & {
    pricing_details?: OutboundPricingDetails
  }
  outboundItem.pricing_details = {
    avg_purchase_price:
      outboundItem.pricing_details?.avg_purchase_price ?? pricingContext.value.avgPurchasePrice,
    selected_unit_price: unitPrice.value,
    margin_amount: outboundItem.pricing_details?.margin_amount ?? 0,
    margin_percent: outboundItem.pricing_details?.margin_percent ?? 0,
    base_price: data.data.base_price,
    suggested_unit_price: data.data.final_price,
    discount_percent: data.data.discount_percent,
    reason: data.data.reason,
    source: data.data.source,
  }
  item.value = outboundItem

  $q.notify({ type: 'positive', message: 'Cena uložena jako zákaznický override' })
}
</script>

<style lang="scss" scoped></style>
