<template>
  <div class="flex flex-col xl:flex-row w-full justify-between items-start xl:items-center gap-5">
    <div class="flex items-start gap-3">
      <IndexRectangle :index="item.index + 1" />
      <div class="flex flex-col gap-2">
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

        <div class="flex flex-wrap gap-2 items-center">
          <ProductAvailability :product-code="item.product.code" />
          <PackageTypeBadge
            v-if="item.desired_package_type_name"
            :package-type="item.desired_package_type_name"
          />
          <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
          <q-btn-dropdown
            v-if="!readonly"
            flat
            dense
            color="primary"
            icon="sym_o_tune"
            label="požadavek"
            dropdown-icon="sym_o_arrow_drop_down"
          >
            <q-list dense>
              <q-item clickable v-close-popup @click="openRequirements('package')">
                <q-item-section avatar>
                  <q-icon name="sym_o_package_2" />
                </q-item-section>
                <q-item-section>Typ balení</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="openRequirements('batch')">
                <q-item-section avatar>
                  <q-icon name="sym_o_barcode" />
                </q-item-section>
                <q-item-section>Šarže</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="clearRequirements">
                <q-item-section avatar>
                  <q-icon name="sym_o_layers_clear" />
                </q-item-section>
                <q-item-section>Vymazat požadavek</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>
        </div>
      </div>
    </div>

    <div
      class="flex flex-col xl:flex-row gap-3 flex-1 items-start xl:items-center justify-start lg:justify-end flex-nowrap"
    >
      <q-input
        v-model.number="item.amount"
        :readonly="readonly"
        dense
        outlined
        label="Počet"
        @update:model-value="update('amount')"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ item.product.unit }}</span>
        </template>
      </q-input>

      <SellingPriceEditor
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
        :can-persist-override="!!customerCode && !readonly"
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
        @click="$emit('remove')"
      />
    </div>
  </div>

  <OutboundOrderItemRequirementsDialog
    v-model:show="requirementsDialog"
    :product-name="item.product.name"
    :initial-mode="requirementsMode"
    :desired-package-type-name="item.desired_package_type_name"
    :desired-batch-code="item.desired_batch_code"
    @save="saveRequirements"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder,
  warehouseApiRoutesProductUpsertProductCustomerPriceOverride,
  type OutboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { round } from '@/utils/round'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import IndexRectangle from '../IndexRectangle.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import SellingPriceEditor from './SellingPriceEditor.vue'
import OutboundOrderItemRequirementsDialog from './OutboundOrderItemRequirementsDialog.vue'

type RequirementMode = 'package' | 'batch'

type OutboundPricingDetails = {
  base_price?: number
  avg_purchase_price?: number
  suggested_unit_price?: number
  discount_percent?: number
  reason?: string
  source?: string
}

const $q = useQuasar()
const { onResponse } = useApi()

const props = defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  customerCode?: string
}>()

defineEmits<{ (e: 'remove'): void }>()

const item = defineModel<OutboundOrderItemSchema>('item', {
  required: true,
})

const totalPrice = ref(round(item.value.unit_price * item.value.amount))
const unitPrice = ref(round(item.value.unit_price))
const isPersistingOverride = ref(false)
const requirementsDialog = ref(false)
const requirementsMode = ref<RequirementMode>('package')

const pricingContext = computed(() => {
  const pricing = item.value.pricing_details as OutboundPricingDetails | undefined
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

const computeUnitFromTotal = () => {
  if (!item.value.amount) {
    return 0
  }
  return round(totalPrice.value / item.value.amount)
}

const update = async (changedField: 'amount' | 'unit' | 'total' | 'requirements') => {
  if (changedField === 'total') {
    unitPrice.value = computeUnitFromTotal()
  } else if (changedField !== 'requirements') {
    totalPrice.value = round(item.value.amount * round(unitPrice.value))
  }

  const res = await warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder({
    path: { order_code: props.orderCode },
    body: {
      product_code: item.value.product.code,
      product_name: item.value.product.name,
      amount: item.value.amount,
      total_price: totalPrice.value,
      unit_price: unitPrice.value,
      index: item.value.index,
      desired_package_type_name: item.value.desired_package_type_name,
      desired_batch_code: item.value.desired_batch_code,
    },
  })

  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
    totalPrice.value = data.data.total_price
    unitPrice.value = data.data.unit_price
    $q.notify({ type: 'positive', message: 'Položka aktualizována' })
  }
}

const openRequirements = (mode: RequirementMode) => {
  requirementsMode.value = mode
  requirementsDialog.value = true
}

const clearRequirements = async () => {
  item.value.desired_package_type_name = null
  item.value.desired_batch_code = null
  await update('requirements')
}

const saveRequirements = async (payload: {
  desired_package_type_name: string | null
  desired_batch_code: string | null
}) => {
  item.value.desired_package_type_name = payload.desired_package_type_name
  item.value.desired_batch_code = payload.desired_batch_code
  await update('requirements')
}

const persistOverrideForCustomer = async () => {
  if (!props.customerCode) {
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
  if (!data?.data) {
    return
  }

  item.value.pricing_details = {
    avg_purchase_price:
      item.value.pricing_details?.avg_purchase_price ?? pricingContext.value.avgPurchasePrice,
    selected_unit_price: unitPrice.value,
    margin_amount: item.value.pricing_details?.margin_amount ?? 0,
    margin_percent: item.value.pricing_details?.margin_percent ?? 0,
    base_price: data.data.base_price,
    suggested_unit_price: data.data.final_price,
    discount_percent: data.data.discount_percent,
    reason: data.data.reason,
    source: data.data.source,
  }

  $q.notify({ type: 'positive', message: 'Cena uložena jako zákaznický override' })
}
</script>
