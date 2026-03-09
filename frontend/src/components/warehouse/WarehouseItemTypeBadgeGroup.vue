<template>
  <div class="flex items-center gap-1">
    <TrackingLevelBadge :level="item.tracking_level" />
    <BatchBadge v-if="item.batch" :batch-code="item.batch.primary_barcode?.code" />
    <PackageTypeBadge v-else :package-type="item.package?.type" />
  </div>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'
import TrackingLevelBadge from './TrackingLevelBadge.vue'
import BatchBadge from './BatchBadge.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'

defineProps<{
  item: WarehouseItemSchema
}>()
</script>

<style scoped></style>
