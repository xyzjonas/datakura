<template>
  <q-card flat bordered class="bg-transparent">
    <q-card-section class="flex items-center justify-between gap-2">
      <div class="min-w-0">
        <div class="text-gray-5 text-xs">Evidence</div>
        <TrackingLevelBadge :level="item.tracking_level" />
      </div>
      <div class="text-right min-w-0">
        <div class="text-gray-5 text-xs">Baleni</div>
        <PackageTypeBadge :package-type="item.package?.type" />
      </div>
    </q-card-section>

    <q-separator />

    <q-card-section class="space-y-2">
      <div v-if="!aggregate" class="flex items-center justify-between gap-2">
        <span class="text-gray-5">EAN</span>
        <a
          class="link truncate max-w-48 text-right"
          @click="$router.push({ name: 'warehouseItemDetail', params: { itemId: item.id } })"
        >
          {{ item.primary_barcode ?? '-' }}
        </a>
      </div>

      <div v-if="!aggregate" class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Pocet v baleni</span>
        <WarehouseItemCountBadge :item="item" />
      </div>

      <div v-else class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Kusu baleni</span>
        <span>{{ aggregatedItemsCount ?? '-' }}</span>
      </div>

      <div v-if="aggregate" class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Velikost baleni</span>
        <span>
          {{ item.package ? `${item.package.amount} x ${item.unit_of_measure}` : '-' }}
        </span>
      </div>

      <div v-if="aggregate" class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Pocet celkem</span>
        <span>{{ item.amount }}</span>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WarehouseItemSchema } from '@/client'
import type { WarehouseItemSchemaWithCount } from '@/utils/aggregatePackaging'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import TrackingLevelBadge from '../warehouse/TrackingLevelBadge.vue'
import WarehouseItemCountBadge from './WarehouseItemCountBadge.vue'

const props = defineProps<{
  item: WarehouseItemSchema | WarehouseItemSchemaWithCount
  aggregate: boolean
}>()

const hasItemsCount = (
  item: WarehouseItemSchema | WarehouseItemSchemaWithCount,
): item is WarehouseItemSchemaWithCount => {
  return 'itemsCount' in item
}

const aggregatedItemsCount = computed(() => {
  return hasItemsCount(props.item) ? props.item.itemsCount : undefined
})
</script>

<style lang="scss" scoped></style>
