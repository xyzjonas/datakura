<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-3xl max-w-[92vw]">
      <div class="p-4 flex flex-col gap-4">
        <!-- Header -->
        <div class="flex items-start gap-2">
          <div class="flex flex-col gap-1">
            <span class="text-2xl uppercase">Vychystat položku</span>
            <span class="text-gray-5 text-sm">{{ item.product.name }}</span>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <!-- Requirement badges -->
        <div class="flex flex-wrap gap-2 items-center">
          <PackageTypeBadge
            v-if="item.desired_package_type_name"
            :package-type="item.desired_package_type_name"
          />
          <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
        </div>

        <!-- STEP 1: Location Suggestions -->
        <template v-if="currentStep === 'suggest'">
          <div class="text-sm text-gray-5 uppercase tracking-wide">Kde hledat</div>
          <q-list bordered separator class="rounded-sm overflow-hidden">
            <q-item v-for="loc in locationGroups" :key="loc.code">
              <q-item-section avatar>
                <q-icon name="sym_o_shelves" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ loc.warehouseName }} / {{ loc.code }}</q-item-label>
                <q-item-label caption>{{ loc.count }} položek</q-item-label>
              </q-item-section>
            </q-item>

            <q-item v-if="!loadingSuggestions && locationGroups.length === 0">
              <q-item-section>
                <q-item-label>Žádné dostupné položky.</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <div class="flex justify-end gap-2">
            <q-btn
              unelevated
              color="primary"
              label="Naskenovat kód"
              icon="qr_code_scanner"
              @click="currentStep = 'scan'"
            />
          </div>
        </template>

        <!-- STEP 2: Barcode Scan Input -->
        <template v-else-if="currentStep === 'scan'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="resetToSuggestions" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Naskenujte kód</span>
          </div>

          <div class="flex flex-col justify-center items-center gap-3 py-4">
            <q-icon name="qr_code_scanner" size="64px" color="primary" />
            <q-input
              v-model="scannedBarcode"
              autofocus
              no-error-icon
              input-class="text-center text-xl"
              inputmode="none"
              class="w-full max-w-xs"
              placeholder="naskenujte položku…"
              @update:model-value="onBarcodeInput"
            />
            <span v-if="lookupError" class="text-negative text-sm">{{ lookupError }}</span>
          </div>

          <q-inner-loading :showing="lookupLoading" />
        </template>

        <!-- STEP 3a: Serialized Item Confirmed -->
        <template v-else-if="currentStep === 'confirm-serialized'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Položka nalezena</span>
          </div>

          <div class="flex flex-col gap-3">
            <div class="bg-positive-1 p-4 rounded-xl flex items-center gap-3">
              <q-icon name="check_circle" color="positive" size="48px" />
              <div class="flex flex-col gap-1">
                <span class="text-lg font-semibold">{{
                  lookupResult?.warehouse_item?.product.name
                }}</span>
                <span class="text-sm text-gray-6">
                  Lokace: {{ lookupResult?.warehouse_item?.location.code }}
                </span>
                <div class="flex gap-2 flex-wrap">
                  <WarehouseItemAmountBadge
                    v-if="lookupResult?.warehouse_item"
                    :item="lookupResult.warehouse_item"
                  />
                  <WarehouseItemTypeBadgeGroup
                    v-if="lookupResult?.warehouse_item"
                    :item="lookupResult.warehouse_item"
                  />
                </div>
              </div>
            </div>

            <!-- Partial pick option for packages with amount > 1 -->
            <div v-if="canPickPartial" class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství</div>
              <q-btn-toggle
                v-model="partialPick"
                :options="[
                  { label: 'Celý balík', value: false },
                  { label: 'Částečně', value: true },
                ]"
                unelevated
                toggle-color="primary"
              />

              <q-input
                v-if="partialPick"
                v-model.number="pickAmount"
                type="number"
                label="Množství k vychystání"
                :rules="[
                  (val) => val > 0 || 'Množství musí být kladné',
                  (val) =>
                    val <= (lookupResult?.warehouse_item?.amount ?? 0) ||
                    'Překročeno dostupné množství',
                ]"
                outlined
                dense
              >
                <template #append>
                  <span class="text-gray-5">{{
                    lookupResult?.warehouse_item?.unit_of_measure
                  }}</span>
                </template>
              </q-input>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :loading="assigning"
              @click="confirmSerializedPick"
            />
          </div>
        </template>

        <!-- STEP 3b: Fungible/Batch - Location and Amount Selection -->
        <template v-else-if="currentStep === 'pick-fungible'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">
              {{ lookupResult?.entity_type === 'batch' ? 'Šarže nalezena' : 'Produkt nalezen' }}
            </span>
          </div>

          <div class="flex flex-col gap-3">
            <div class="bg-blue-1 p-4 rounded-xl">
              <div class="font-semibold">
                {{ lookupResult?.batch?.description ?? lookupResult?.product?.name ?? 'Položka' }}
              </div>
              <div class="text-sm text-gray-6">
                Dostupných položek: {{ lookupResult?.matching_items?.length ?? 0 }}
              </div>
            </div>

            <!-- Location selection if multiple locations -->
            <div v-if="fungibleLocations.length > 1" class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Vyberte lokaci</div>
              <q-list bordered separator class="rounded-xl overflow-hidden">
                <q-item
                  v-for="loc in fungibleLocations"
                  :key="loc.code"
                  clickable
                  :active="selectedLocation === loc.code"
                  @click="selectedLocation = loc.code"
                >
                  <q-item-section avatar>
                    <q-radio v-model="selectedLocation" :val="loc.code" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ loc.warehouseName }} / {{ loc.code }}</q-item-label>
                    <q-item-label caption>{{ loc.totalAmount }} {{ loc.unit }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>

            <!-- Amount input -->
            <div class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství k vychystání</div>
              <q-input
                v-model.number="pickAmount"
                type="number"
                :rules="[
                  (val) => val > 0 || 'Množství musí být kladné',
                  (val) => val <= maxAvailableInLocation || `Max: ${maxAvailableInLocation}`,
                ]"
                outlined
                dense
                autofocus
              >
                <template #append>
                  <span class="text-gray-5">{{ unitOfMeasure }}</span>
                </template>
              </q-input>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :disable="!selectedLocation || pickAmount <= 0"
              :loading="assigning"
              @click="confirmFungiblePick"
            />
          </div>
        </template>

        <!-- STEP 3c: Location Scan Fallback -->
        <template v-else-if="currentStep === 'confirm-location'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Lokace nalezena</span>
          </div>

          <div class="flex flex-col gap-3">
            <div class="bg-blue-1 p-4 rounded-xl">
              <div class="font-semibold">
                {{ lookupResult?.location?.warehouse_name }} / {{ lookupResult?.location?.code }}
              </div>
              <div class="text-sm text-gray-6">
                Položek na lokaci: {{ lookupResult?.matching_items?.length ?? 0 }}
              </div>
            </div>

            <!-- Item selection for serialized items -->
            <div v-if="hasSerializedItems" class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Vyberte položku</div>
              <q-list bordered separator class="rounded-xl overflow-hidden">
                <q-item
                  v-for="matchedItem in lookupResult?.matching_items"
                  :key="matchedItem.id"
                  clickable
                  :active="selectedWarehouseItemId === matchedItem.id"
                  @click="selectedWarehouseItemId = matchedItem.id"
                >
                  <q-item-section avatar>
                    <q-radio v-model="selectedWarehouseItemId" :val="matchedItem.id" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ matchedItem.product.name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side class="items-end gap-2">
                    <WarehouseItemAmountBadge :item="matchedItem" />
                    <WarehouseItemTypeBadgeGroup :item="matchedItem" />
                  </q-item-section>
                </q-item>
              </q-list>
            </div>

            <!-- Amount input for fungible items -->
            <div v-else class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství k vychystání</div>
              <q-input
                v-model.number="pickAmount"
                type="number"
                :rules="[
                  (val) => val > 0 || 'Množství musí být kladné',
                  (val) => val <= maxAvailableInLocation || `Max: ${maxAvailableInLocation}`,
                ]"
                outlined
                dense
                autofocus
              >
                <template #append>
                  <span class="text-gray-5">{{ unitOfMeasure }}</span>
                </template>
              </q-input>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :disable="hasSerializedItems ? !selectedWarehouseItemId : pickAmount <= 0"
              :loading="assigning"
              @click="confirmLocationPick"
            />
          </div>
        </template>

        <q-inner-loading :showing="loadingSuggestions" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  type OutboundWarehouseOrderItemSchema,
  type WarehouseItemSchema,
  type BarcodeLookupResponse,
  warehouseApiRoutesProductGetProductWarehouseInfo,
  warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAppSettings } from '@/composables/use-app-settings'
import { useBarcodeLookup } from '@/composables/use-barcode-lookup'
import { computed, ref, watch } from 'vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemTypeBadgeGroup from '../warehouse/WarehouseItemTypeBadgeGroup.vue'

type Step = 'suggest' | 'scan' | 'confirm-serialized' | 'pick-fungible' | 'confirm-location'

const props = defineProps<{
  warehouseOrderCode: string
  item: OutboundWarehouseOrderItemSchema
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })
const { onResponse } = useApi()
const { scannerMode } = useAppSettings()
const { lookup, loading: lookupLoading, error: lookupError } = useBarcodeLookup()

// State
const currentStep = ref<Step>('suggest')
const scannedBarcode = ref('')
const lookupResult = ref<BarcodeLookupResponse | null>(null)
const selectedWarehouseItemId = ref<number | null>(null)
const selectedLocation = ref<string | null>(null)
const pickAmount = ref<number>(0)
const partialPick = ref(false)
const loadingSuggestions = ref(false)
const allCandidates = ref<WarehouseItemSchema[]>([])
const assigning = ref(false)

// Computed - Location suggestions
type LocationGroup = { code: string; warehouseName: string; count: number }

const locationGroups = computed<LocationGroup[]>(() => {
  const map = new Map<string, LocationGroup>()
  for (const c of allCandidates.value) {
    const key = c.location.code
    if (map.has(key)) {
      map.get(key)!.count++
    } else {
      map.set(key, { code: key, warehouseName: c.location.warehouse_name, count: 1 })
    }
  }
  return Array.from(map.values())
})

// Computed - Serialized item partial pick
const canPickPartial = computed(() => {
  const item = lookupResult.value?.warehouse_item
  if (!item) return false
  const isSerialized =
    item.tracking_level === 'SERIALIZED_PACKAGE' || item.tracking_level === 'SERIALIZED_PIECE'
  return isSerialized && item.amount > 1
})

// Computed - Fungible location groups
type FungibleLocation = {
  code: string
  warehouseName: string
  totalAmount: number
  unit: string
}

const fungibleLocations = computed<FungibleLocation[]>(() => {
  const items = lookupResult.value?.matching_items ?? []
  const map = new Map<string, FungibleLocation>()

  for (const item of items) {
    const key = item.location.code
    if (map.has(key)) {
      map.get(key)!.totalAmount += item.amount
    } else {
      map.set(key, {
        code: key,
        warehouseName: item.location.warehouse_name,
        totalAmount: item.amount,
        unit: item.unit_of_measure,
      })
    }
  }

  return Array.from(map.values())
})

const maxAvailableInLocation = computed(() => {
  if (!selectedLocation.value) return 0
  const loc = fungibleLocations.value.find((l) => l.code === selectedLocation.value)
  return loc?.totalAmount ?? 0
})

const unitOfMeasure = computed(() => {
  const items = lookupResult.value?.matching_items ?? []
  return items[0]?.unit_of_measure ?? ''
})

const hasSerializedItems = computed(() => {
  const items = lookupResult.value?.matching_items ?? []
  return items.some(
    (item) =>
      item.tracking_level === 'SERIALIZED_PACKAGE' || item.tracking_level === 'SERIALIZED_PIECE',
  )
})

// Actions
const loadSuggestions = async () => {
  loadingSuggestions.value = true
  const response = await warehouseApiRoutesProductGetProductWarehouseInfo({
    path: { product_code: props.item.product.code },
    query: {
      package_type_name: props.item.desired_package_type_name ?? undefined,
      batch_code: props.item.desired_batch_code ?? undefined,
    },
  })
  const data = onResponse(response)
  allCandidates.value = (data?.data ?? []).flatMap((wh) => wh.locations.flatMap((loc) => loc.items))
  loadingSuggestions.value = false
}

const resetToSuggestions = () => {
  currentStep.value = 'suggest'
  scannedBarcode.value = ''
  lookupResult.value = null
  selectedWarehouseItemId.value = null
  selectedLocation.value = null
  pickAmount.value = 0
  partialPick.value = false
}

const onBarcodeInput = async (barcode: string | number | null) => {
  if (!barcode || typeof barcode !== 'string' || barcode.length < 3) return

  const result = await lookup(barcode, props.item.product.code)
  if (!result || !result.found) {
    return
  }

  lookupResult.value = result

  // Route to appropriate step based on entity type
  if (result.entity_type === 'warehouse_item') {
    const item = result.warehouse_item
    if (!item) return

    // Check if this is a serialized item
    if (
      item.tracking_level === 'SERIALIZED_PACKAGE' ||
      item.tracking_level === 'SERIALIZED_PIECE'
    ) {
      currentStep.value = 'confirm-serialized'
      pickAmount.value = item.amount

      // Auto-confirm in scanner mode after delay
      if (scannerMode.value && !canPickPartial.value) {
        setTimeout(() => {
          void confirmSerializedPick()
        }, 400)
      }
    } else {
      // Fungible/batch item - need location and amount
      currentStep.value = 'pick-fungible'
      selectedLocation.value = item.location.code
      pickAmount.value = Number(props.item.amount)
    }
  } else if (result.entity_type === 'batch' || result.entity_type === 'product') {
    currentStep.value = 'pick-fungible'
    // Auto-select location if only one
    if (fungibleLocations.value.length === 1) {
      selectedLocation.value = fungibleLocations.value[0].code
    }
    pickAmount.value = Number(props.item.amount)
  } else if (result.entity_type === 'location') {
    currentStep.value = 'confirm-location'
    selectedLocation.value = result.location?.code ?? null
    pickAmount.value = Number(props.item.amount)
    // Auto-select first item if only one
    if (result.matching_items?.length === 1) {
      selectedWarehouseItemId.value = result.matching_items[0].id
    }
  }
}

const confirmSerializedPick = async () => {
  const warehouseItemId = lookupResult.value?.warehouse_item?.id
  if (!warehouseItemId) return

  assigning.value = true
  try {
    const amount = partialPick.value ? pickAmount.value : null
    await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: warehouseItemId,
        amount: amount !== null ? String(amount) : null,
      },
    })
    emit('confirm')
    showDialog.value = false
  } finally {
    assigning.value = false
  }
}

const confirmFungiblePick = async () => {
  if (!selectedLocation.value) return

  // Find first warehouse item in the selected location
  const items = lookupResult.value?.matching_items ?? []
  const itemInLocation = items.find((item) => item.location.code === selectedLocation.value)
  if (!itemInLocation) return

  assigning.value = true
  try {
    await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: itemInLocation.id,
        amount: String(pickAmount.value),
      },
    })
    emit('confirm')
    showDialog.value = false
  } finally {
    assigning.value = false
  }
}

const confirmLocationPick = async () => {
  let warehouseItemId: number

  if (hasSerializedItems.value) {
    if (!selectedWarehouseItemId.value) return
    warehouseItemId = selectedWarehouseItemId.value
  } else {
    // Fungible - use first item in location
    const items = lookupResult.value?.matching_items ?? []
    const itemInLocation = items[0]
    if (!itemInLocation) return
    warehouseItemId = itemInLocation.id
  }

  assigning.value = true
  try {
    await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: warehouseItemId,
        amount: hasSerializedItems.value ? null : String(pickAmount.value),
      },
    })
    emit('confirm')
    showDialog.value = false
  } finally {
    assigning.value = false
  }
}

// Watchers
watch(
  () => showDialog.value,
  (opened) => {
    if (opened) {
      resetToSuggestions()
      void loadSuggestions()
    }
  },
)

// Auto-select first location if only one for fungible
watch(fungibleLocations, (locations) => {
  if (currentStep.value === 'pick-fungible' && locations.length === 1 && !selectedLocation.value) {
    selectedLocation.value = locations[0].code
  }
})
</script>
