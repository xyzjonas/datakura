<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-3xl max-w-[92vw]">
      <div class="p-4 flex flex-col gap-4">
        <!-- Header -->
        <div class="flex items-start gap-2">
          <div class="flex flex-col gap-1">
            <span class="text-2xl uppercase">Vybrat skladovou položku</span>
            <span class="text-gray-5 text-sm">{{ item.product.name }}</span>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <!-- Requirement badges + filter toggle -->
        <div class="flex flex-wrap gap-2 items-center">
          <PackageTypeBadge
            v-if="item.desired_package_type_name"
            :package-type="item.desired_package_type_name"
          />
          <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
          <q-space />
          <q-toggle
            v-if="item.desired_package_type_name || item.desired_batch_code"
            v-model="ignoreFilters"
            label="ignorovat filtry"
            dense
            size="sm"
            color="warning"
          />
        </div>

        <!-- STEP 1: location list -->
        <template v-if="selectedLocation === null">
          <div class="text-sm text-gray-5 uppercase tracking-wide">Vyberte lokaci</div>
          <q-list bordered separator class="rounded-xl overflow-hidden">
            <q-item
              v-for="loc in locationGroups"
              :key="loc.code"
              clickable
              @click="selectLocation(loc.code)"
            >
              <q-item-section avatar>
                <q-icon name="sym_o_shelves" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ loc.warehouseName }} / {{ loc.code }}</q-item-label>
                <q-item-label caption>{{ loc.count }} položek</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" />
              </q-item-section>
            </q-item>

            <q-item v-if="!loading && locationGroups.length === 0">
              <q-item-section>
                <q-item-label>Žádná skladová položka neodpovídá požadavku.</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <div class="flex justify-end gap-2">
            <q-btn flat label="obnovit" @click="loadCandidates" :loading="loading" />
          </div>
        </template>

        <!-- STEP 2a: WebUI – item list within location -->
        <template v-else-if="!scannerMode">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="selectedLocation = null" />
            <span class="text-sm uppercase tracking-wide text-gray-5">
              {{ selectedLocation }}
            </span>
          </div>
          <q-list bordered separator class="rounded-xl overflow-hidden">
            <q-item
              v-for="candidate in visibleItemsInLocation"
              :key="candidate.id"
              clickable
              @click="selectedId = candidate.id"
            >
              <q-item-section avatar>
                <q-radio v-model="selectedId" :val="candidate.id" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ candidate.product.name }}</q-item-label>
                <q-item-label caption>
                  {{ candidate.location.warehouse_name }} / {{ candidate.location.code }}
                </q-item-label>
              </q-item-section>
              <q-item-section side class="items-end gap-2">
                <WarehouseItemAmountBadge :item="candidate" />
                <WarehouseItemTypeBadgeGroup :item="candidate" />
              </q-item-section>
            </q-item>
          </q-list>

          <div
            v-if="itemsInLocation.length > ITEMS_VISIBLE_LIMIT"
            class="text-sm text-gray-5 text-center"
          >
            Zobrazeno {{ ITEMS_VISIBLE_LIMIT }} z {{ itemsInLocation.length }} položek — vyberte
            konkrétní lokaci pro přesnější výsledky
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="selectedLocation = null" />
            <q-btn
              unelevated
              color="primary"
              label="přiřadit"
              :disable="selectedId === null"
              :loading="loading"
              @click="confirm"
            />
          </div>
        </template>

        <!-- STEP 2b: Scanner – scan to confirm -->
        <template v-else>
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="selectedLocation = null" />
            <span class="text-sm uppercase tracking-wide text-gray-5">
              {{ selectedLocation }}
            </span>
          </div>

          <div class="flex flex-col justify-center items-center gap-3 py-4">
            <span class="text-gray-5 text-sm uppercase tracking-wide">VYBRÁNO</span>
            <span class="text-2xl">
              <span class="text-gray-5">LOKACE </span>{{ selectedLocation }}
            </span>
            <q-input
              v-model="scanConfirmation"
              autofocus
              :rules="[(val) => val === selectedLocation || 'Naskenujte správnou lokaci']"
              no-error-icon
              input-class="text-center text-xl"
              inputmode="none"
              class="w-full max-w-xs"
              placeholder="naskenujte lokaci…"
            />
            <span class="text-gray-5 text-sm uppercase">POTVRDIT LOKACI SCANNEREM</span>
            <transition mode="out-in" name="slide-fade">
              <q-btn
                v-if="scanConfirmation.length >= 1 && scanConfirmation !== selectedLocation"
                label="reset"
                flat
                @click="scanConfirmation = ''"
              />
            </transition>
          </div>

          <div v-if="scanConfirmed" class="text-center text-positive text-sm">
            Lokace potvrzena — položka bude přiřazena automaticky
          </div>
        </template>

        <q-inner-loading :showing="loading" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  type OutboundWarehouseOrderItemSchema,
  type WarehouseItemSchema,
  warehouseApiRoutesProductGetProductWarehouseInfo,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAppSettings } from '@/composables/use-app-settings'
import { computed, ref, watch } from 'vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemTypeBadgeGroup from '../warehouse/WarehouseItemTypeBadgeGroup.vue'

const ITEMS_VISIBLE_LIMIT = 10

const props = defineProps<{
  warehouseOrderCode: string
  item: OutboundWarehouseOrderItemSchema
}>()

const emit = defineEmits<{
  (e: 'confirm', warehouseItemId: number): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })
const { onResponse } = useApi()
const { scannerMode } = useAppSettings()

const allCandidates = ref<WarehouseItemSchema[]>([])
const loading = ref(false)
const selectedId = ref<number | null>(null)
const selectedLocation = ref<string | null>(null)
const ignoreFilters = ref(false)
const scanConfirmation = ref('')
const scanConfirmed = ref(false)

// ---- derived data ----

const candidates = computed(() => allCandidates.value)

type LocationGroup = { code: string; warehouseName: string; count: number }

const locationGroups = computed<LocationGroup[]>(() => {
  const map = new Map<string, LocationGroup>()
  for (const c of candidates.value) {
    const key = c.location.code
    if (map.has(key)) {
      map.get(key)!.count++
    } else {
      map.set(key, { code: key, warehouseName: c.location.warehouse_name, count: 1 })
    }
  }
  return Array.from(map.values())
})

const itemsInLocation = computed<WarehouseItemSchema[]>(() =>
  candidates.value.filter((c) => c.location.code === selectedLocation.value),
)

const visibleItemsInLocation = computed<WarehouseItemSchema[]>(() =>
  itemsInLocation.value.slice(0, ITEMS_VISIBLE_LIMIT),
)

// ---- actions ----

const loadCandidates = async () => {
  loading.value = true
  const response = await warehouseApiRoutesProductGetProductWarehouseInfo({
    path: { product_code: props.item.product.code },
    query: {
      package_type_name: ignoreFilters.value
        ? undefined
        : (props.item.desired_package_type_name ?? undefined),
      batch_code: ignoreFilters.value ? undefined : (props.item.desired_batch_code ?? undefined),
    },
  })
  const data = onResponse(response)
  // Flatten warehouses → locations → items into a single list
  allCandidates.value = (data?.data ?? []).flatMap((wh) => wh.locations.flatMap((loc) => loc.items))
  loading.value = false
}

const selectLocation = (code: string) => {
  selectedLocation.value = code
  selectedId.value = itemsInLocation.value[0]?.id ?? null
  scanConfirmation.value = ''
  scanConfirmed.value = false
}

const confirm = () => {
  if (selectedId.value === null) return
  emit('confirm', selectedId.value)
  showDialog.value = false
}

// scanner: auto-confirm when scanned text matches location
watch(scanConfirmation, (val) => {
  if (val === selectedLocation.value && itemsInLocation.value.length > 0) {
    scanConfirmed.value = true
    selectedId.value = itemsInLocation.value[0].id
    setTimeout(() => {
      confirm()
    }, 400)
  }
})

watch(
  () => showDialog.value,
  (opened) => {
    if (opened) {
      selectedLocation.value = null
      selectedId.value = null
      scanConfirmation.value = ''
      scanConfirmed.value = false
      void loadCandidates()
    }
  },
)

// reload when ignoreFilters toggled — drops or re-applies server-side filters
watch(ignoreFilters, () => {
  void loadCandidates()
})
</script>

<style scoped>
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.2s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
