<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <TransitionGroup name="list" tag="div" class="flex flex-col gap-2">
      <InboundWarehouseItemEditableRow
        v-for="(item, index) in items"
        :key="item.id"
        :index="index"
        :item="item"
        :readonly="readonly"
        :allow-move="allowMove"
        :warehouse-order-code="warehouseOrderCode"
        @dissolve-item="() => $emit('dissolveItem', item.id)"
        @packaged="
          (newItems, batch, trackingType) =>
            $emit('packaged', item.id, newItems, batch, trackingType)
        "
        @remove="(amount) => $emit('removeItem', item.id, amount)"
        @moved="(location) => $emit('moved', item.warehouse_item_id!, location)"
        @offloaded="$emit('offloaded')"
      />
    </TransitionGroup>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
      <span v-if="!readonly" class="link uppercase" @click="$emit('addItem')">přidat položku</span>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type {
  BatchSchema,
  InboundWarehouseOrderItemSchema,
  WarehouseItemSchema,
  WarehouseLocationSchema,
} from '@/client'
import type { TrackingType } from './InboundWarehouseOrderTrackDialog.vue'
import EmptyPanel from '../EmptyPanel.vue'
import InboundWarehouseItemEditableRow from './InboundWarehouseItemEditableRow.vue'

defineEmits<{
  (e: 'dissolveItem', itemId: number): void
  (e: 'removeItem', itemId: number, amount: number): void
  (e: 'addItem'): void
  (
    e: 'packaged',
    orderItemId: number,
    items: WarehouseItemSchema[],
    batch: BatchSchema | undefined,
    trackingType: TrackingType,
  ): void
  (e: 'moved', warehouseItemId: number, location: WarehouseLocationSchema): void
  (e: 'offloaded'): void
}>()
defineProps<{
  items: InboundWarehouseOrderItemSchema[]
  readonly?: boolean
  allowMove?: boolean
  warehouseOrderCode?: string
}>()
</script>
