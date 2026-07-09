<template>
  <div>
    <!-- Context: item header shown once resolved -->
    <div v-if="resolvedItem" class="mb-4">
      <stock-product-link :product="resolvedItem.product" :class="'link text-xl'" />
      <div class="text-muted text-xs">{{ resolvedItem.product.code }}</div>
      <div class="text-sm text-muted mt-1 flex gap-3 flex-wrap">
        <span>{{ resolvedItem.location?.code }}</span>
        <span>{{ resolvedItem.amount }} {{ resolvedItem.unit_of_measure }}</span>
        <span v-if="resolvedItem.batch">
          Šarže {{ resolvedItem.batch.primary_barcode?.code ?? resolvedItem.batch.id }}
        </span>
      </div>
      <q-separator class="mt-3" />
    </div>

    <!-- STEP: scan-item -->
    <template v-if="step === 'scan-item'">
      <div class="text-base font-semibold mb-1">Skenujte položku</div>
      <div class="text-sm text-muted mb-4">Naskenujte čárový kód položky, šarže nebo produktu</div>
      <q-input
        ref="itemInputRef"
        v-model="barcodeValue"
        outlined
        autofocus
        label="Čárový kód"
        :loading="lookupLoading"
        :error="!!lookupError"
        :error-message="lookupError ?? undefined"
        @keydown.enter.prevent="fireBarcodeImmediately"
      />
    </template>

    <!-- STEP: scan-source-location (product barcode scanned) -->
    <template v-else-if="step === 'scan-source-location'">
      <div class="text-xl font-bold mb-1">{{ resolvedProduct?.name }}</div>
      <div class="text-sm text-muted mb-4">Naskenujte aktuální umístění produktu</div>
      <q-input
        ref="sourceLocationInputRef"
        v-model="sourceLocationCode"
        outlined
        autofocus
        label="Zdrojové místo (kód)"
        :loading="sourceLocationLoading"
        :error="!!sourceLocationError"
        :error-message="sourceLocationError ?? undefined"
        @keydown.enter.prevent="fireSourceLocationImmediately"
      />
      <q-btn flat label="Zpět" @click="reset" class="mt-3" />
    </template>

    <!-- STEP: pick-item (multiple items matched) -->
    <template v-else-if="step === 'pick-item'">
      <div class="text-sm text-muted mb-3">Vyberte položku k přesunu:</div>
      <q-list separator class="rounded border">
        <q-item
          v-for="item in matchingItems"
          :key="item.id"
          clickable
          v-ripple
          @click="selectItem(item)"
        >
          <q-item-section>
            <q-item-label
              >{{ item.product.name }} ·
              <small class="text-muted">{{ item.primary_barcode }}</small></q-item-label
            >
            <q-item-label caption>
              {{ item.location?.code }} · {{ item.amount }} {{ item.unit_of_measure }}
              <span v-if="item.batch">
                · {{ item.batch.primary_barcode?.code ?? item.batch.id }}
              </span>
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="sym_o_chevron_right" />
          </q-item-section>
        </q-item>
      </q-list>
      <q-btn flat label="Zpět" @click="reset" class="mt-3" />
    </template>

    <!-- STEP: enter-amount (BATCH / FUNGIBLE) -->
    <template v-else-if="step === 'enter-amount'">
      <div class="text-sm text-muted mb-4">
        Zadejte množství k přesunu (max {{ resolvedItem?.amount }}
        {{ resolvedItem?.unit_of_measure }})
      </div>
      <q-input
        ref="amountInputRef"
        v-model.number="amount"
        outlined
        autofocus
        type="number"
        label="Množství"
        :rules="[amountRule]"
        @keydown.enter.prevent="proceedFromAmount"
      />
      <div class="flex gap-2 mt-3">
        <q-btn flat label="Zpět" @click="reset" />
        <q-btn
          color="primary"
          class="flex-1"
          label="Potvrdit množství"
          :disable="!isAmountValid"
          @click="proceedFromAmount"
        />
      </div>
    </template>

    <!-- STEP: scan-location -->
    <template v-else-if="step === 'scan-location'">
      <div v-if="amount !== null" class="text-sm text-muted mb-1">
        Množství: {{ amount }} {{ resolvedItem?.unit_of_measure }}
      </div>
      <div class="text-sm text-muted mb-4">Naskenujte cílové skladové místo</div>
      <q-input
        ref="locationInputRef"
        v-model="locationCode"
        outlined
        autofocus
        label="Cílové místo (kód)"
        :loading="submitLoading"
        :error="!!submitError"
        :error-message="submitError ?? undefined"
        @keydown.enter.prevent="fireLocationImmediately"
      />
      <q-btn flat label="Zpět" @click="reset" class="mt-3" />
    </template>
  </div>
</template>

<script setup lang="ts">
import {
  type BarcodeLookupResponse,
  type WarehouseItemSchema,
  warehouseApiRoutesProductGetProductWarehouseInfo,
  warehouseApiRoutesWarehouseCreateMovement,
  warehouseApiRoutesWarehouseGetWarehouseLocations,
} from '@/client'
import { useBarcodeLookup } from '@/composables/use-barcode-lookup'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import StockProductLink from '../links/StockProductLink.vue'

type Step = 'scan-item' | 'scan-source-location' | 'pick-item' | 'enter-amount' | 'scan-location'
type ProductInfo = NonNullable<BarcodeLookupResponse['product']>

const emit = defineEmits<{
  (e: 'done'): void
}>()

const { lookup, loading: lookupLoading, error: lookupError } = useBarcodeLookup()

const step = ref<Step>('scan-item')
const barcodeValue = ref('')
const resolvedItem = ref<WarehouseItemSchema | null>(null)
const resolvedProduct = ref<ProductInfo | null>(null)
const matchingItems = ref<WarehouseItemSchema[]>([])
const amount = ref<number | null>(null)
const locationCode = ref('')
const sourceLocationCode = ref('')
const sourceLocationLoading = ref(false)
const sourceLocationError = ref<string | null>(null)
const submitLoading = ref(false)
const submitError = ref<string | null>(null)

const itemInputRef = ref<{ $el: HTMLElement } | null>(null)
const sourceLocationInputRef = ref<{ $el: HTMLElement } | null>(null)
const amountInputRef = ref<{ $el: HTMLElement } | null>(null)
const locationInputRef = ref<{ $el: HTMLElement } | null>(null)

const needsAmount = computed(
  () =>
    resolvedItem.value?.tracking_level === 'BATCH' ||
    resolvedItem.value?.tracking_level === 'FUNGIBLE',
)

const isAmountValid = computed(() => {
  if (!resolvedItem.value || amount.value === null || amount.value === undefined) return false
  return amount.value > 0 && amount.value <= Number(resolvedItem.value.amount)
})

const amountRule = (val: number | null) => {
  if (val === null || val === undefined) return 'Zadejte množství'
  if (val <= 0) return 'Množství musí být kladné'
  if (resolvedItem.value && val > Number(resolvedItem.value.amount))
    return `Maximálně ${resolvedItem.value.amount}`
  return true
}

const reset = () => {
  step.value = 'scan-item'
  barcodeValue.value = ''
  resolvedItem.value = null
  resolvedProduct.value = null
  matchingItems.value = []
  amount.value = null
  locationCode.value = ''
  sourceLocationCode.value = ''
  sourceLocationError.value = null
  submitError.value = null
  nextTick(() => {
    itemInputRef.value?.$el?.querySelector('input')?.focus()
  })
}

const setItem = (item: WarehouseItemSchema) => {
  resolvedItem.value = item
  amount.value = null
  if (needsAmount.value) {
    step.value = 'enter-amount'
    nextTick(() => amountInputRef.value?.$el?.querySelector('input')?.focus())
  } else {
    step.value = 'scan-location'
    nextTick(() => locationInputRef.value?.$el?.querySelector('input')?.focus())
  }
}

const selectItem = (item: WarehouseItemSchema) => setItem(item)

const proceedFromAmount = () => {
  if (!isAmountValid.value) return
  step.value = 'scan-location'
  nextTick(() => locationInputRef.value?.$el?.querySelector('input')?.focus())
}

// ── Debounce: item barcode ──────────────────────────────────────────────────

let itemTimer: ReturnType<typeof setTimeout> | null = null

watch(barcodeValue, (val) => {
  if (step.value !== 'scan-item') return
  if (itemTimer) clearTimeout(itemTimer)
  if (!val) return
  itemTimer = setTimeout(onBarcodeScan, 500)
})

const fireBarcodeImmediately = () => {
  if (itemTimer) clearTimeout(itemTimer)
  onBarcodeScan()
}

const onBarcodeScan = async () => {
  if (!barcodeValue.value) return
  const result = await lookup(barcodeValue.value)
  if (!result?.found) return

  if (result.entity_type === 'warehouse_item' && result.warehouse_item) {
    setItem(result.warehouse_item)
  } else if (
    (result.entity_type === 'batch' || result.entity_type === 'location') &&
    result.matching_items
  ) {
    if (result.matching_items.length === 1) {
      setItem(result.matching_items[0])
    } else if (result.matching_items.length > 1) {
      matchingItems.value = result.matching_items
      step.value = 'pick-item'
    }
  } else if (result.entity_type === 'product' && result.product) {
    resolvedProduct.value = result.product
    step.value = 'scan-source-location'
    nextTick(() => sourceLocationInputRef.value?.$el?.querySelector('input')?.focus())
  }
}

// ── Debounce: source location (product barcode flow) ───────────────────────

let sourceLocationTimer: ReturnType<typeof setTimeout> | null = null

watch(sourceLocationCode, (val) => {
  if (step.value !== 'scan-source-location') return
  sourceLocationError.value = null
  if (sourceLocationTimer) clearTimeout(sourceLocationTimer)
  if (!val) return
  sourceLocationTimer = setTimeout(onSourceLocationScan, 500)
})

const fireSourceLocationImmediately = () => {
  if (sourceLocationTimer) clearTimeout(sourceLocationTimer)
  onSourceLocationScan()
}

const onSourceLocationScan = async () => {
  if (!sourceLocationCode.value || !resolvedProduct.value) return
  sourceLocationError.value = null
  sourceLocationLoading.value = true

  try {
    // Find the location by code
    const locResult = await warehouseApiRoutesWarehouseGetWarehouseLocations({
      query: { search_term: sourceLocationCode.value, page_size: 10 },
    })
    const locations = locResult.data?.data ?? []
    const exactMatch = locations.find((l) => l.code === sourceLocationCode.value)
    const match = exactMatch ?? (locations.length === 1 ? locations[0] : null)

    if (!match) {
      sourceLocationError.value = `Místo '${sourceLocationCode.value}' nenalezeno`
      return
    }

    // Get all warehouse items for this product, filter to the found location
    const productResult = await warehouseApiRoutesProductGetProductWarehouseInfo({
      path: { product_code: resolvedProduct.value.code },
    })
    const allItems: WarehouseItemSchema[] = []
    for (const wh of productResult.data?.data ?? []) {
      for (const loc of wh.locations) {
        allItems.push(...loc.items)
      }
    }
    const items = allItems.filter((i) => i.location?.code === match.code)

    if (items.length === 0) {
      sourceLocationError.value = `Na místě '${match.code}' nejsou zásoby produktu`
      return
    }

    if (items.length === 1) {
      setItem(items[0])
    } else {
      matchingItems.value = items
      step.value = 'pick-item'
    }
  } finally {
    sourceLocationLoading.value = false
  }
}

// ── Debounce: destination location → auto-submit ───────────────────────────

let locationTimer: ReturnType<typeof setTimeout> | null = null

watch(locationCode, (val) => {
  if (step.value !== 'scan-location') return
  submitError.value = null
  if (locationTimer) clearTimeout(locationTimer)
  if (!val) return
  locationTimer = setTimeout(onLocationScan, 500)
})

const fireLocationImmediately = () => {
  if (locationTimer) clearTimeout(locationTimer)
  onLocationScan()
}

const onLocationScan = async () => {
  if (!locationCode.value || !resolvedItem.value) return
  submitError.value = null
  submitLoading.value = true

  try {
    const locResult = await warehouseApiRoutesWarehouseGetWarehouseLocations({
      query: { search_term: locationCode.value, page_size: 10 },
    })
    const locations = locResult.data?.data ?? []
    const exactMatch = locations.find((l) => l.code === locationCode.value)
    const match = exactMatch ?? (locations.length === 1 ? locations[0] : null)

    if (!match) {
      submitError.value = `Místo '${locationCode.value}' nenalezeno`
      return
    }

    const body: { item_id: number; location_to_code: string; amount?: number } = {
      item_id: resolvedItem.value.id,
      location_to_code: match.code,
    }
    if (needsAmount.value && amount.value !== null) {
      body.amount = amount.value
    }

    const result = await warehouseApiRoutesWarehouseCreateMovement({ body })
    if (result.response.ok) {
      emit('done')
    } else {
      const err = result.error as { error?: { exception?: string } } | undefined
      submitError.value = err?.error?.exception ?? result.response.statusText
    }
  } finally {
    submitLoading.value = false
  }
}

onUnmounted(() => {
  if (itemTimer) clearTimeout(itemTimer)
  if (sourceLocationTimer) clearTimeout(sourceLocationTimer)
  if (locationTimer) clearTimeout(locationTimer)
})
</script>
