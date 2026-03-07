<template>
  <div class="simple_list_item justify-between">
    <span class="text-gray-5">{{ formatDateTimeLong(movement.moved_at) }}</span>

    {{ movement.location_from_code }} → {{ movement.location_to_code }}
    <warehouse-item-amount-badge
      :item="{ amount: movement.amount, unit_of_measure: movement.stock_product.unit }"
    />
    <!-- <q-item-section>
      <q-item-label> {{ movement.stock_product_code }} · {{ movement.amount }} MJ </q-item-label>
      <q-item-label caption>
        {{ movement.location_from_code ?? '—' }} → {{ movement.location_to_code ?? '—' }}
      </q-item-label>
    </q-item-section>
    <q-item-section side>
      <q-item-label caption>
        {{ new Date(movement.moved_at).toLocaleString('cs-CZ') }}
      </q-item-label>
    </q-item-section> -->
  </div>
</template>

<script setup lang="ts">
import type { WarehouseMovementSchema } from '@/client'
import WarehouseItemAmountBadge from './WarehouseItemAmountBadge.vue'
import { formatDateTimeLong } from '@/utils/date'

defineProps<{ index: number; movement: WarehouseMovementSchema }>()
</script>

<style lang="scss" scoped></style>
