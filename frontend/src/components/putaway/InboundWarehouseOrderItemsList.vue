<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <!-- <q-list separator> -->
    <TransitionGroup name="list" tag="div" class="flex">
      <div v-for="(item, index) in items" :key="item.id" clickable class="simple_list_item">
        <IndexRectangle :index="index + 1" />
        <WarehouseItemEditableRow
          :item="item"
          :readonly="readonly"
          :allow-move="allowMove"
          @dissolve-item="() => $emit('dissolveItem', item.id)"
          @packaged="(items) => $emit('packaged', item, items)"
          @remove="(amount) => $emit('removeItem', item.id, amount)"
          @moved="(location) => $emit('moved', item.id, location)"
          class="flex-1"
        ></WarehouseItemEditableRow>
      </div>
    </TransitionGroup>
    <!-- </q-list> -->
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
      <span v-if="!readonly" class="link uppercase" @click="$emit('addItem')">přidat položku</span>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema, WarehouseLocationSchema } from '@/client'
import EmptyPanel from '../EmptyPanel.vue'
import WarehouseItemEditableRow from './WarehouseItemEditableRow.vue'
import IndexRectangle from '../IndexRectangle.vue'

defineEmits<{
  (e: 'dissolveItem', itemId: number): void
  (e: 'removeItem', itemId: number, amount: number): void
  (e: 'addItem'): void
  (e: 'packaged', item: WarehouseItemSchema, items: WarehouseItemSchema[]): void
  (e: 'moved', itemId: number, location: WarehouseLocationSchema): void
}>()
defineProps<{
  items: WarehouseItemSchema[]
  readonly?: boolean
  allowMove?: boolean
}>()
</script>
