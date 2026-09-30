<template>
  <q-badge :color="getSnapshotCoverageTone(snapshot)" class="capitalize">
    {{ getSnapshotCoverageLabel(snapshot) }}
  </q-badge>
</template>

<script setup lang="ts">
import type { InventorySnapshotCoverageLike } from '@/views/inventory-snapshot'
import { getSnapshotCoverageLabel, getSnapshotCoverageTone } from '@/views/inventory-snapshot'

defineProps<{
  snapshot: InventorySnapshotCoverageLike
}>()
</script>
