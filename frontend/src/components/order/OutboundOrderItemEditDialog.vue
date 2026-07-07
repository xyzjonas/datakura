<template>
  <q-dialog v-model="show">
    <q-card class="flex flex-col" style="width: 600px; max-width: 95vw">
      <q-card-section class="flex items-start gap-3 pb-3">
        <div class="flex-1 min-w-0">
          <router-link
            :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
            class="link text-base font-semibold leading-tight"
            >{{ item.product.name }}</router-link
          >
          <div class="text-xs text-gray-5 mt-0.5">{{ item.product.code }}</div>
        </div>
        <q-btn flat round dense icon="sym_o_close" v-close-popup class="mt-0.5" />
      </q-card-section>

      <q-separator />

      <q-card-section class="flex flex-col gap-6 pt-5 overflow-auto">
        <ProductAvailability :product-code="item.product.code" />

        <!-- Amount -->
        <div class="flex flex-col gap-2">
          <div class="section-label">Množství</div>
          <q-input
            v-model.number="item.amount"
            dense
            outlined
            label="Počet"
            @update:model-value="update('amount')"
            :debounce="500"
          >
            <template #append>
              <span class="text-xs text-gray-6">{{ item.product.unit }}</span>
            </template>
          </q-input>
        </div>

        <!-- Pricing -->
        <div class="flex flex-col gap-2">
          <div class="section-label">Cena</div>
          <div class="flex flex-wrap gap-4 items-start">
            <SellingPriceEditor
              v-model="unitPrice"
              :currency="currency"
              :unit="item.product.unit"
              :base-price="pricingContext.basePrice"
              :suggested-price="pricingContext.suggestedUnitPrice"
              :avg-purchase-price="pricingContext.avgPurchasePrice"
              :discount-percent="pricingContext.discountPercent"
              :reason="pricingContext.reason"
              :price-source="pricingContext.source"
              :can-persist-override="!!customerCode"
              :override-saving="isPersistingOverride"
              @update:model-value="update('unit')"
              @persist-override="persistOverrideForCustomer"
              class="w-full"
            />
            <q-input
              v-model.number="totalPrice"
              @update:model-value="update('total')"
              dense
              outlined
              label="Celková cena"
              :debounce="500"
              class="w-full"
            >
              <template #append>
                <span class="text-xs text-gray-6">{{ currency }}</span>
              </template>
            </q-input>
          </div>
        </div>

        <!-- Requirements -->
        <div class="flex flex-col gap-2">
          <div class="section-label">Požadavky</div>
          <div class="flex items-center gap-2 flex-wrap">
            <PackageTypeBadge
              v-if="item.desired_package_type_name"
              :package-type="item.desired_package_type_name"
            />
            <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
            <q-btn-dropdown
              flat
              dense
              color="primary"
              icon="sym_o_tune"
              label="požadavek"
              dropdown-icon="sym_o_arrow_drop_down"
            >
              <q-list dense>
                <q-item clickable v-close-popup @click="openRequirements('package')">
                  <q-item-section avatar><q-icon name="sym_o_package_2" /></q-item-section>
                  <q-item-section>Typ balení</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="openRequirements('batch')">
                  <q-item-section avatar><q-icon name="sym_o_barcode" /></q-item-section>
                  <q-item-section>Šarže</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="clearRequirements">
                  <q-item-section avatar><q-icon name="sym_o_layers_clear" /></q-item-section>
                  <q-item-section>Vymazat požadavek</q-item-section>
                </q-item>
              </q-list>
            </q-btn-dropdown>
          </div>
        </div>

        <!-- Note -->
        <div class="flex flex-col gap-1">
          <div class="section-label">Poznámka</div>
          <q-btn
            flat
            dense
            no-caps
            size="sm"
            :icon="showNote ? 'expand_less' : 'expand_more'"
            :label="showNote ? 'Skrýt' : item.note ? 'Zobrazit' : 'Přidat'"
            class="self-start text-muted"
            @click="toggleNote"
          />
          <q-input
            v-if="showNote"
            v-model.trim="item.note"
            outlined
            dense
            label="Poznámka k položce"
            type="textarea"
            autogrow
            :debounce="600"
            @update:model-value="update('note')"
          />
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>

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
import { computed, ref, watch } from 'vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import OutboundOrderItemRequirementsDialog from './OutboundOrderItemRequirementsDialog.vue'
import SellingPriceEditor from './SellingPriceEditor.vue'

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
  orderCode: string
  customerCode?: string
}>()

const show = defineModel<boolean>('show', { default: false })
const item = defineModel<OutboundOrderItemSchema>('item', { required: true })

const totalPrice = ref(round(item.value.unit_price * item.value.amount))
const unitPrice = ref(round(item.value.unit_price))
const isPersistingOverride = ref(false)
const requirementsDialog = ref(false)
const requirementsMode = ref<RequirementMode>('package')
const showNote = ref(!!item.value.note)

watch(show, (visible) => {
  if (visible) {
    totalPrice.value = round(item.value.unit_price * item.value.amount)
    unitPrice.value = round(item.value.unit_price)
    showNote.value = !!item.value.note
  }
})

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
  if (!item.value.amount) return 0
  return round(totalPrice.value / item.value.amount)
}

const toggleNote = () => {
  showNote.value = !showNote.value
  if (!showNote.value) {
    item.value.note = null
    void update('note')
  }
}

const update = async (changedField: 'amount' | 'unit' | 'total' | 'requirements' | 'note') => {
  if (changedField === 'total') {
    unitPrice.value = computeUnitFromTotal()
  } else if (changedField !== 'requirements' && changedField !== 'note') {
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
      note: item.value.note,
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
  if (!props.customerCode) return
  isPersistingOverride.value = true
  const response = await warehouseApiRoutesProductUpsertProductCustomerPriceOverride({
    path: { product_code: item.value.product.code },
    body: { customer_code: props.customerCode, fixed_price: unitPrice.value },
  })
  isPersistingOverride.value = false
  const data = onResponse(response)
  if (!data?.data) return
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

<style scoped>
.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--q-color-grey-7, #616161);
}
</style>
