<template>
  <q-markup-table flat class="bg-transparent">
    <thead>
      <tr>
        <th class="text-left">Skladová položka</th>
        <th class="text-left">Místo</th>
        <th class="text-left">Množství</th>
        <th class="text-left">
          {{ valuationMode === 'purchase' ? 'Cena / MJ při uložení' : 'Cena / MJ při příjmu' }}
        </th>
        <th class="text-left">
          {{ valuationMode === 'purchase' ? 'Hodnota při uložení' : 'Hodnota při příjmu' }}
        </th>
        <th class="text-left">Příjmová cena</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="line in group.lines" :key="line.id">
        <td>
          <div class="flex items-center gap-3">
            <TrackingLevelBadge :level="line.tracking_level" />
            <div class="text-muted text-xs">#{{ line.warehouse_item_id_at_snapshot }}</div>
            <WarehouseItemLink v-if="line.warehouse_item_id" :item-id="line.warehouse_item_id" />
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
          <q-badge :color="line.receipt_price_available ? 'positive' : 'warning'" class="uppercase">
            {{ line.receipt_price_available ? 'Zdroj nalezen' : 'Bez příjmu' }}
          </q-badge>
        </td>
      </tr>
    </tbody>
  </q-markup-table>
</template>

<script setup lang="ts">
import WarehouseItemLink from '@/components/links/WarehouseItemLink.vue'
import TrackingLevelBadge from '@/components/warehouse/TrackingLevelBadge.vue'
import {
  formatMoney,
  getSnapshotLineUnitPrice,
  getSnapshotLineValue,
  type InventorySnapshotProductGroup,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'

defineProps<{
  group: InventorySnapshotProductGroup
  valuationMode: InventorySnapshotValuationMode
}>()
</script>
