<template>
  <div
    v-if="product"
    class="flex flex-col gap-2 rounded border border-solid border-gray-3 p-3"
    data-test="pricing-panel"
  >
    <!-- 1. purchase price: current -> new -->
    <div class="flex items-baseline justify-between gap-2 flex-wrap">
      <span class="text-sm text-gray-6">Nákupní cena</span>
      <div class="flex items-baseline gap-2" data-test="purchase-delta">
        <span class="tabular-nums" data-test="purchase-current">
          {{ currentPurchasePrice.toFixed(2) }}
        </span>
        <q-icon name="sym_o_arrow_forward" size="xs" class="text-gray-5" />
        <strong class="tabular-nums text-base" data-test="purchase-new">
          {{ newPurchasePrice.toFixed(2) }} {{ currency }}
        </strong>
      </div>
    </div>
    <div
      class="flex items-center justify-end gap-2 text-sm font-medium"
      :class="deltaClass"
      data-test="purchase-delta-values"
    >
      <q-icon :name="deltaIcon" size="xs" />
      <span v-if="delta.percent !== null">{{ formatDeltaPercent(delta) }}</span>
      <span>({{ formatDeltaAmount(delta) }} {{ currency }})</span>
    </div>

    <q-separator />

    <!-- 2. + 4. base selling price, editable -->
    <div class="flex items-center gap-2">
      <q-input
        v-model.number="draftBasePrice"
        class="flex-1"
        dense
        outlined
        type="number"
        min="0"
        step="0.01"
        label="Základní prodejní cena"
        :rules="[(v: unknown) => (Number(v) >= 0 && v !== '') || 'Neplatná cena']"
        hide-bottom-space
        data-test="base-price-input"
      >
        <template #append>
          <span class="text-xs text-gray-6">{{ currency }} / {{ unit }}</span>
        </template>
      </q-input>
      <q-btn
        v-if="isDirty"
        dense
        flat
        round
        icon="sym_o_restart_alt"
        color="grey-6"
        data-test="base-price-reset"
        @click="draftBasePrice = product.base_price"
      >
        <q-tooltip>Vrátit na aktuální ({{ product.base_price.toFixed(2) }})</q-tooltip>
      </q-btn>
      <q-btn
        v-if="isDirty"
        dense
        unelevated
        no-caps
        color="primary"
        icon="sym_o_save"
        label="Uložit"
        :loading="saving"
        :disable="!isValid"
        data-test="base-price-save"
        @click="save"
      />
    </div>
    <div v-if="isDirty" class="text-xs text-gray-6 text-right" data-test="base-price-hint">
      Aktuální základní cena: {{ product.base_price.toFixed(2) }} {{ currency }}
    </div>

    <!-- 3. margin / markup incl. the new purchase price -->
    <div class="grid grid-cols-3 gap-2 text-center text-xs" data-test="impact">
      <div class="flex flex-col">
        <span class="text-gray-6">Marže</span>
        <MarginPercent :margin="margin" :danger="belowMinimum" data-test="impact-margin" />
        <span class="text-gray-5">nyní {{ formatMarginPercent(currentMargin) }}</span>
      </div>
      <div class="flex flex-col">
        <span class="text-gray-6">Přirážka</span>
        <MarginPercent :margin="margin" markup :danger="belowMinimum" data-test="impact-markup" />
        <span class="text-gray-5">nyní {{ formatMarkupPercent(currentMargin) }}</span>
      </div>
      <div class="flex flex-col">
        <span class="text-gray-6">Zisk / {{ unit }}</span>
        <MarginText :margin="margin" :currency="currency" :danger="belowMinimum" />
        <span class="text-gray-5">nyní {{ formatMargin(currentMargin) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductUpdateProductBasePrice, type ProductSchema } from '@/client'
import { loadMinimumMarkupPercent, useMinimumProfit } from '@/composables/use-minimum-profit'
import { useApi } from '@/composables/use-api'
import {
  calculateMargin,
  formatMargin,
  formatMarginPercent,
  formatMarkupPercent,
} from '@/utils/margin'
import { isBelowMinimumProfit } from '@/utils/minimum-profit'
import {
  calculatePurchasePriceDelta,
  formatDeltaAmount,
  formatDeltaPercent,
} from '@/utils/price-impact'
import { useQuasar } from 'quasar'
import { computed, onMounted, ref, watch } from 'vue'
import MarginPercent from './MarginPercent.vue'
import MarginText from './MarginText.vue'

const props = defineProps<{
  currency: string
  /** unit price of the stock about to be bought */
  newPurchasePrice: number
}>()

/** The product; replaced by the server response once the base price got saved. */
const product = defineModel<ProductSchema | undefined>('product', { required: true })

const $q = useQuasar()
const { onResponse } = useApi()
const { minimumMarkupPercent, enabled } = useMinimumProfit()

const unit = computed(() => product.value?.unit ?? '')
const currentPurchasePrice = computed(() => Number(product.value?.purchase_price ?? 0))

const draftBasePrice = ref<number | string>(product.value?.base_price ?? 0)
watch(
  () => [product.value?.code, product.value?.base_price] as const,
  () => {
    draftBasePrice.value = product.value?.base_price ?? 0
  },
)

const draftNumber = computed(() => Number(draftBasePrice.value))
const isValid = computed(
  () => draftBasePrice.value !== '' && Number.isFinite(draftNumber.value) && draftNumber.value >= 0,
)
const isDirty = computed(
  () =>
    !!product.value &&
    isValid.value &&
    Math.abs(draftNumber.value - product.value.base_price) >= 0.005,
)

const delta = computed(() =>
  calculatePurchasePriceDelta(currentPurchasePrice.value, props.newPurchasePrice),
)
// buying more expensive is bad news, cheaper is good news
const deltaClass = computed(() =>
  delta.value.amount > 0.005
    ? 'text-negative'
    : delta.value.amount < -0.005
      ? 'text-positive'
      : 'text-gray-6',
)
const deltaIcon = computed(() =>
  delta.value.amount > 0.005
    ? 'sym_o_trending_up'
    : delta.value.amount < -0.005
      ? 'sym_o_trending_down'
      : 'sym_o_trending_flat',
)

const sellingPrice = computed(() => (isValid.value ? draftNumber.value : 0))
const margin = computed(() => calculateMargin(sellingPrice.value, props.newPurchasePrice))
const currentMargin = computed(() =>
  calculateMargin(sellingPrice.value, currentPurchasePrice.value),
)
const belowMinimum = computed(() =>
  isBelowMinimumProfit(sellingPrice.value, props.newPurchasePrice, minimumMarkupPercent.value),
)

const saving = ref(false)
const save = async () => {
  if (!product.value || !isDirty.value) {
    return
  }
  saving.value = true
  try {
    const res = await warehouseApiRoutesProductUpdateProductBasePrice({
      path: { product_code: product.value.code },
      body: { base_price: draftNumber.value },
    })
    const data = onResponse(res)
    if (data?.data) {
      product.value = data.data
      $q.notify({ type: 'positive', message: 'Základní prodejní cena uložena' })
    }
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (!enabled.value) {
    loadMinimumMarkupPercent().catch(() => undefined)
  }
})
</script>
