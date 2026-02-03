<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <ForegroundPanel v-for="(item, index) in items" :key="item.code">
      <WarehouseItemEditableRow
        v-model:item="items[index]"
        :readonly="readonly"
        @remove-item="() => $emit('removeItem', item.code)"
        @packaged="(items) => $emit('packaged', item, items)"
      ></WarehouseItemEditableRow>
    </ForegroundPanel>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
      <span class="link uppercase" @click="$emit('addItem')">přidat položku</span>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'
import ForegroundPanel from '../ForegroundPanel.vue'
import EmptyPanel from '../EmptyPanel.vue'
import WarehouseItemEditableRow from './WarehouseItemEditableRow.vue'

defineEmits<{
  (e: 'removeItem', itemCode: string): void
  (e: 'addItem'): void
  (e: 'packaged', item: WarehouseItemSchema, items: WarehouseItemSchema[]): void
}>()
defineProps<{ readonly?: boolean }>()
const items = defineModel<Array<WarehouseItemSchema>>('items', { default: [] })
</script>
