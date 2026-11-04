<template>
  <ForegroundPanel no-padding>
    <q-expansion-item v-model="expanded" expand-separator header-class="px-4 py-3" class="rounded">
      <template #header>
        <div class="grid w-full lg:grid-cols-[1fr_2fr_1fr] items-start md:items-center gap-4">
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
                {{ valuationMode === 'purchase' ? 'Cena při snapshotu' : 'Cena při příjmu' }}
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

      <!-- a snapshot can hold thousands of lines: only render the table of opened groups -->
      <div v-if="everExpanded" class="px-4 pb-4 pt-1">
        <InventorySnapshotLinesTable :group="group" :valuation-mode="valuationMode" />
      </div>
    </q-expansion-item>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InventorySnapshotLinesTable from '@/components/warehouse/InventorySnapshotLinesTable.vue'
import InventorySnapshotReceiptCoverageBadge from '@/components/warehouse/InventorySnapshotReceiptCoverageBadge.vue'
import { useAppRouter } from '@/composables/use-app-router'
import {
  formatSnapshotTotals,
  type InventorySnapshotProductGroup,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'
import { ref, watch } from 'vue'

defineProps<{
  group: InventorySnapshotProductGroup
  valuationMode: InventorySnapshotValuationMode
}>()

const { goToProduct } = useAppRouter()
const expanded = ref(false)
// keep the table mounted after the first opening (no re-render on every toggle)
const everExpanded = ref(false)
watch(expanded, (value) => {
  if (value) {
    everExpanded.value = true
  }
})
</script>
