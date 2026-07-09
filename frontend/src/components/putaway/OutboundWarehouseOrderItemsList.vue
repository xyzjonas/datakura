<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <TransitionGroup name="list" class="flex">
      <OutboundWarehouseOrderItemRow
        v-for="(item, index) in items"
        :key="item.id"
        :index="index"
        :item="item"
        :warehouse-order-code="warehouseOrderCode"
        @updated="(order) => $emit('updated', order)"
        class="flex-1"
      />
    </TransitionGroup>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage" class="min-h-xs">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { OutboundWarehouseOrderItemSchema, OutboundWarehouseOrderSchema } from '@/client'
import EmptyPanel from '../EmptyPanel.vue'
import OutboundWarehouseOrderItemRow from './OutboundWarehouseOrderItemRow.vue'

defineProps<{
  items: OutboundWarehouseOrderItemSchema[]
  warehouseOrderCode: string
}>()

defineEmits<{
  (e: 'updated', order: OutboundWarehouseOrderSchema): void
}>()
</script>
