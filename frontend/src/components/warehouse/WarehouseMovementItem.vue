<template>
  <div class="simple_list_item items-center justify-between gap-4">
    <div class="flex flex-col gap-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <a
          class="link truncate"
          @click="
            $router.push({
              name: 'productDetail',
              params: { productCode: movement.stock_product.code },
            })
          "
        >
          {{ movement.stock_product.name }}
        </a>
        <span class="text-gray-5">{{ movement.stock_product.code }}</span>
      </div>
      <div class="flex items-center gap-2 flex-wrap text-sm">
        <span
          >{{ movement.location_from_code ?? '—' }} → {{ movement.location_to_code ?? '—' }}</span
        >
        <WarehouseItemTrackingLevelBadge
          v-if="movement.item"
          :level="movement.item.tracking_level"
        />
        <PackageTypeBadge
          v-if="movement.item?.package?.type"
          :package-type="movement.item.package.type"
        />
      </div>
      <span class="text-gray-5 text-xs">{{ formatDateTimeLong(movement.moved_at) }}</span>
    </div>

    <WarehouseItemAmountBadge
      :item="{ amount: movement.amount, unit_of_measure: movement.stock_product.unit }"
    />
  </div>
</template>

<script setup lang="ts">
import type { WarehouseMovementSchema } from '@/client'
import WarehouseItemAmountBadge from './WarehouseItemAmountBadge.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import WarehouseItemTrackingLevelBadge from '../putaway/WarehouseItemTrackingLevelBadge.vue'
import { formatDateTimeLong } from '@/utils/date'

defineProps<{ index: number; movement: WarehouseMovementSchema }>()
</script>

<style lang="scss" scoped></style>
