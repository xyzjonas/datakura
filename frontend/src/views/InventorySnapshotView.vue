<template>
  <div v-if="snapshot" class="flex w-full flex-col gap-3">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <q-breadcrumbs>
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Snapshoty skladu" :to="{ name: 'inventorySnapshots' }" />
        <q-breadcrumbs-el :label="`#${snapshot.id}`" />
      </q-breadcrumbs>

      <InventorySnapshotReceiptCoverageBadge :snapshot="snapshot" />
    </div>

    <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <div class="text-xs uppercase text-muted">Snapshot skladu</div>
        <h1 class="mt-1 text-5xl text-primary">#{{ snapshot.id }}</h1>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-sm text-gray-6">
          <span>{{ formatCapturedAt(snapshot.captured_at) }}</span>
          <span>/</span>
          <span>{{ formatInventorySnapshotTriggerSource(snapshot.trigger_source) }}</span>
          <span>/</span>
          <span>{{ formatInventorySnapshotCadence(snapshot.cadence) }}</span>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-3">
        <ForegroundPanel>
          <div class="text-xs uppercase tracking-wide text-muted">Skladových položek</div>
          <div class="mt-2 text-3xl font-semibold">{{ snapshot.line_count }}</div>
        </ForegroundPanel>
        <InventorySnapshotTotalsPanel
          title="Cena při snapshotu"
          :totals="snapshot.purchase_totals"
          caption="Aktuální nákupní cena produktu v okamžiku snapshotu"
        />
        <InventorySnapshotTotalsPanel
          title="Cena při příjmu"
          :totals="snapshot.receipt_totals"
          caption="Historická cena z příjmové řádky"
          empty-label="Žádné oceněné příjmové řádky"
        />
      </div>
    </div>

    <InventorySnapshotValuationToggle v-model:mode="valuationMode" class="max-w-[36rem]" />

    <ForegroundPanel>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2>Seskupené řádky snapshotu</h2>
            <div class="mt-1 text-sm text-gray-6">
              Snapshot je agregovaný podle skladové karty. Kliknutím se rozbalí jednotlivé položky.
            </div>
          </div>

          <SearchInput
            v-model="productSearch"
            placeholder="Vyhledat skladovou kartu podle kódu nebo názvu"
            clearable
            class="w-full max-w-md"
          />
        </div>

        <div v-if="groupedLines.length" class="flex flex-col gap-2">
          <ForegroundPanel v-for="group in groupedLines" :key="group.productCode" no-padding>
            <q-expansion-item expand-separator header-class="px-4 py-3" class="rounded">
              <template #header>
                <div
                  class="grid w-full lg:grid-cols-[1fr_2fr_1fr] items-start md:items-center gap-4"
                >
                  <div class="min-w-0 flex-1">
                    <button class="text-left" @click.stop="goToProduct(group.productCode)">
                      <div class="font-semibold text-primary">{{ group.productName }}</div>
                      <div class="text-xs text-gray-5">{{ group.productCode }}</div>
                    </button>
                  </div>

                  <div class="grid gap-2 sm:grid-cols-3">
                    <div>
                      <div class="text-[11px] uppercase tracking-wide text-muted">Položek</div>
                      <div class="mt-1 text-sm font-semibold">{{ group.itemCount }}</div>
                    </div>
                    <div>
                      <div class="text-[11px] uppercase tracking-wide text-muted">Množství</div>
                      <div class="mt-1 text-sm font-semibold flex items-center gap-2">
                        {{ group.totalQuantity }}
                        <q-badge color="gray">{{ group.unitOfMeasure }}</q-badge>
                      </div>
                    </div>
                    <div>
                      <div class="text-[11px] uppercase tracking-wide text-muted">
                        {{
                          valuationMode === 'purchase' ? 'Cena při snapshotu' : 'Cena při příjmu'
                        }}
                      </div>
                      <div class="mt-1 text-sm font-semibold text-primary">
                        {{ formatSnapshotTotals(group, valuationMode) }}
                      </div>
                    </div>
                  </div>

                  <div class="shrink-0">
                    <InventorySnapshotReceiptCoverageBadge :snapshot="group" />
                  </div>
                </div>
              </template>

              <div class="px-4 pb-4 pt-1">
                <q-markup-table flat class="bg-transparent">
                  <thead>
                    <tr>
                      <th class="text-left">Skladová položka</th>
                      <th class="text-left">Místo</th>
                      <th class="text-left">Množství</th>
                      <th class="text-left">
                        {{
                          valuationMode === 'purchase'
                            ? 'Cena / MJ při snapshotu'
                            : 'Cena / MJ při příjmu'
                        }}
                      </th>
                      <th class="text-left">
                        {{
                          valuationMode === 'purchase'
                            ? 'Hodnota při snapshotu'
                            : 'Hodnota při příjmu'
                        }}
                      </th>
                      <th class="text-left">Příjmová cena</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="line in group.lines" :key="line.id">
                      <td>
                        <div class="flex items-center gap-3">
                          <TrackingLevelBadge :level="line.tracking_level" />
                          <div class="text-muted text-xs">
                            #{{ line.warehouse_item_id_at_snapshot }}
                          </div>
                          <WarehouseItemLink
                            v-if="line.warehouse_item_id"
                            :item-id="line.warehouse_item_id"
                          />
                        </div>
                      </td>
                      <td>{{ line.location_code }}</td>
                      <td class="flex items-center gap-2">
                        {{ line.quantity }}
                        <q-badge color="gray">{{ group.unitOfMeasure }}</q-badge>
                      </td>
                      <td>
                        <span v-if="getSnapshotLineUnitPrice(line, valuationMode)">
                          {{ formatMoney(getSnapshotLineUnitPrice(line, valuationMode)) }}
                        </span>
                        <span v-else class="text-gray-5">—</span>
                      </td>
                      <td class="font-semibold text-primary">
                        <span v-if="getSnapshotLineValue(line, valuationMode)">
                          {{ formatMoney(getSnapshotLineValue(line, valuationMode)) }}
                        </span>
                        <span v-else class="text-gray-5">—</span>
                      </td>
                      <td>
                        <q-badge
                          :color="line.receipt_price_available ? 'positive' : 'warning'"
                          class="uppercase"
                        >
                          {{ line.receipt_price_available ? 'Zdroj nalezen' : 'Bez příjmu' }}
                        </q-badge>
                      </td>
                    </tr>
                  </tbody>
                </q-markup-table>
              </div>
            </q-expansion-item>
          </ForegroundPanel>
        </div>

        <div v-else class="py-8 text-center text-gray-5">
          Žádná skladová karta neodpovídá hledání.
        </div>
      </div>
    </ForegroundPanel>
  </div>

  <ForegroundPanel v-else class="grid w-full content-center justify-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">SNAPSHOT NENALEZEN</span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type InventorySnapshotDetailSchema,
  warehouseApiRoutesAnalyticsGetInventorySnapshot,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import WarehouseItemLink from '@/components/links/WarehouseItemLink.vue'
import SearchInput from '@/components/SearchInput.vue'
import InventorySnapshotReceiptCoverageBadge from '@/components/warehouse/InventorySnapshotReceiptCoverageBadge.vue'
import InventorySnapshotTotalsPanel from '@/components/warehouse/InventorySnapshotTotalsPanel.vue'
import InventorySnapshotValuationToggle from '@/components/warehouse/InventorySnapshotValuationToggle.vue'
import TrackingLevelBadge from '@/components/warehouse/TrackingLevelBadge.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import {
  filterSnapshotProductGroups,
  formatInventorySnapshotCadence,
  formatInventorySnapshotTriggerSource,
  formatMoney,
  formatSnapshotTotals,
  groupSnapshotLinesByProduct,
  getSnapshotLineUnitPrice,
  getSnapshotLineValue,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'
import { computed, ref } from 'vue'

const props = defineProps<{ snapshotId: string }>()

const { onResponse } = useApi()
const { goToProduct } = useAppRouter()
const valuationMode = ref<InventorySnapshotValuationMode>('purchase')
const productSearch = ref('')
const snapshot = ref<InventorySnapshotDetailSchema>()

const response = await warehouseApiRoutesAnalyticsGetInventorySnapshot({
  path: { snapshot_id: Number(props.snapshotId) },
})
const data = onResponse(response)
if (data) {
  snapshot.value = data.data
}

const formatCapturedAt = (value: string) => {
  return new Date(value).toLocaleString('cs-CZ')
}

const allGroupedLines = computed(() =>
  snapshot.value ? groupSnapshotLinesByProduct(snapshot.value) : [],
)

const groupedLines = computed(() =>
  filterSnapshotProductGroups(allGroupedLines.value, productSearch.value),
)
</script>
