<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <TransitionGroup name="list" tag="div" class="flex">
      <div v-for="(item, index) in items" :key="item.id" class="simple_list_item">
        <IndexRectangle :index="index + 1" />
        <OutboundWarehouseOrderItemRow
          :item="item"
          :warehouse-order-code="warehouseOrderCode"
          @updated="(order) => $emit('updated', order)"
          class="flex-1"
        />
      </div>
    </TransitionGroup>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { OutboundWarehouseOrderItemSchema, OutboundWarehouseOrderSchema } from '@/client'
import EmptyPanel from '../EmptyPanel.vue'
import IndexRectangle from '../IndexRectangle.vue'
import OutboundWarehouseOrderItemRow from './OutboundWarehouseOrderItemRow.vue'

defineProps<{
  items: OutboundWarehouseOrderItemSchema[]
  warehouseOrderCode: string
}>()

defineEmits<{
  (e: 'updated', order: OutboundWarehouseOrderSchema): void
}>()
</script>
