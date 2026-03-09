<template>
  <div class="flex items-center w-full gap-1">
    <span class="w-4 text-gray-5">{{ index + 1 }}</span>
    <div class="flex flex-col gap-1">
      <span>{{ item.product.name }}</span>
      <div class="flex gap-1">
        <TrackingLevelBadge :level="item.tracking_level" />
        <BatchBadge v-if="item.batch" :batch-code="item.batch.primary_barcode?.code" />
        <PackageTypeBadge v-else :package-type="item.package?.type" />
      </div>
    </div>
    <!-- <div class="flex items-center gap-2">
      <q-badge class="py-1">
        <q-icon name="sym_o_package_2" class="mr-1" />
        {{ item.package?.type ?? 'Skladem volně' }}
      </q-badge>
    </div> -->
    <div class="ml-auto flex items-center">
      <span v-if="item.package" class="text-gray-5 text-xs mr-1">V balení:</span>
      <span class="flex flex-nowrap items-center">
        <WarehouseItemAmountBadge :item="item" :amount="amount" />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import TrackingLevelBadge from '../warehouse/TrackingLevelBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
defineProps<{ readonly?: boolean; index: number; amount?: number }>()
defineEmits(['dissolveItem'])

const item = defineModel<WarehouseItemSchema>('item', { required: true })
</script>

<style lang="scss" scoped></style>
