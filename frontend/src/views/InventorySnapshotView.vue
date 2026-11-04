<template>
  <div v-if="snapshot" class="flex w-full flex-col gap-3">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <q-breadcrumbs>
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Stavy skladu" :to="{ name: 'inventorySnapshots' }" />
        <q-breadcrumbs-el :label="`#${snapshot.id}`" />
      </q-breadcrumbs>

      <InventorySnapshotReceiptCoverageBadge :snapshot="snapshot" />
    </div>

    <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <div class="text-xs uppercase text-muted">Stav skladu</div>
        <h1 class="mt-1 text-5xl text-primary">#{{ snapshot.id }}</h1>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-sm text-gray-6">
          <span>{{ formatCapturedAt(snapshot.captured_at) }}</span>
          <span>/</span>
          <span>{{ formatInventorySnapshotTriggerSource(snapshot.trigger_source) }}</span>
          <span>/</span>
          <span>{{ formatInventorySnapshotCadence(snapshot.cadence) }}</span>
        </div>
      </div>
    </div>

    <InventorySnapshotHeader :snapshot="snapshot" :valuation-mode="valuationMode" />

    <ForegroundPanel>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2>Seskupené řádky stavu skladu</h2>
            <div class="mt-1 text-sm text-gray-6">
              Stav skladu je agregovaný podle skladové karty. Kliknutím se rozbalí jednotlivé
              položky.
            </div>
          </div>

          <SearchInput
            v-model="productSearch"
            placeholder="Vyhledat podle kódu, názvu nebo lokace"
            clearable
            :debounce="300"
            class="w-full max-w-md"
          />
        </div>

        <InventorySnapshotValuationSwitch v-model:mode="valuationMode" />

        <div v-if="groupedLines.length" class="flex flex-col gap-2">
          <InventorySnapshotGroupPanel
            v-for="group in groupedLines"
            :key="group.productCode"
            :group="group"
            :valuation-mode="valuationMode"
          />
        </div>

        <div v-else-if="!loading" class="py-8 text-center text-gray-5">
          Žádná skladová karta neodpovídá hledání.
        </div>

        <div class="flex items-center justify-between gap-3 text-sm text-gray-6">
          <span>Načteno {{ lines.length }} / {{ totalCount }} položek</span>
          <q-btn
            v-if="hasMore"
            outline
            color="primary"
            label="Načíst další"
            no-caps
            :loading="loading"
            @click="loadPage(page + 1)"
          />
        </div>
      </div>
    </ForegroundPanel>
  </div>

  <ForegroundPanel v-else class="grid w-full content-center justify-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">STAV SKLADU NENALEZEN</span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type InventorySnapshotDetailSchema,
  type InventorySnapshotLineSchema,
  warehouseApiRoutesAnalyticsGetInventorySnapshot,
  warehouseApiRoutesAnalyticsGetInventorySnapshotItems,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import SearchInput from '@/components/SearchInput.vue'
import InventorySnapshotGroupPanel from '@/components/warehouse/InventorySnapshotGroupPanel.vue'
import InventorySnapshotHeader from '@/components/warehouse/InventorySnapshotHeader.vue'
import InventorySnapshotReceiptCoverageBadge from '@/components/warehouse/InventorySnapshotReceiptCoverageBadge.vue'
import InventorySnapshotValuationSwitch from '@/components/warehouse/InventorySnapshotValuationSwitch.vue'
import { useApi } from '@/composables/use-api'
import {
  formatInventorySnapshotCadence,
  formatInventorySnapshotTriggerSource,
  groupSnapshotLinesByProduct,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'
import { computed, ref, watch } from 'vue'

const PAGE_SIZE = 100

const props = defineProps<{ snapshotId: string }>()

const { onResponse } = useApi()
const valuationMode = ref<InventorySnapshotValuationMode>('purchase')
const productSearch = ref('')
const snapshot = ref<InventorySnapshotDetailSchema>()

const lines = ref<InventorySnapshotLineSchema[]>([])
const page = ref(1)
const totalCount = ref(0)
const hasMore = ref(false)
const loading = ref(false)
// guards against out-of-order responses when the search changes while a page is loading
let requestId = 0

const loadPage = async (pageNumber: number) => {
  const currentRequest = ++requestId
  loading.value = true
  try {
    const response = await warehouseApiRoutesAnalyticsGetInventorySnapshotItems({
      path: { snapshot_id: Number(props.snapshotId) },
      query: {
        page: pageNumber,
        page_size: PAGE_SIZE,
        search: productSearch.value || undefined,
      },
    })
    const data = onResponse(response)
    if (!data || currentRequest !== requestId) {
      return
    }
    lines.value = pageNumber === 1 ? data.data : [...lines.value, ...data.data]
    page.value = pageNumber
    totalCount.value = data.count
    hasMore.value = data.next !== null
  } finally {
    if (currentRequest === requestId) {
      loading.value = false
    }
  }
}

const response = await warehouseApiRoutesAnalyticsGetInventorySnapshot({
  path: { snapshot_id: Number(props.snapshotId) },
})
const data = onResponse(response)
if (data) {
  snapshot.value = data.data
  await loadPage(1)
}

watch(productSearch, () => loadPage(1))

const formatCapturedAt = (value: string) => {
  return new Date(value).toLocaleString('cs-CZ')
}

const groupedLines = computed(() => groupSnapshotLinesByProduct(lines.value))
</script>
