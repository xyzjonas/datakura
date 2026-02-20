<template>
  <div v-if="items.length > 0" class="flex flex-col gap-2">
    <q-list separator>
      <q-item
        v-for="(item, index) in items"
        :key="item.id"
        clickable
        class="w-full flex items-center gap-5"
      >
        <span
          class="font-mono text-lg border light:border-gray-3 dark:border-gray-5 aspect-ratio-square grid content-center justify-center rounded w-12"
          >{{ index + 1 }}</span
        >
        <WarehouseItemEditableRow
          v-model:item="items[index]"
          :readonly="readonly"
          :allow-move="allowMove"
          @dissolve-item="() => $emit('dissolveItem', item.id)"
          @packaged="(items) => $emit('packaged', item, items)"
          @remove="(amount) => $emit('removeItem', item.id, amount)"
          @moved="(location) => $emit('moved', item.id, location)"
          class="flex-1"
        ></WarehouseItemEditableRow>
      </q-item>
    </q-list>
    <!-- </ForegroundPanel> -->
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
      <span class="link uppercase" @click="$emit('addItem')">přidat položku</span>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema, WarehouseLocationSchema } from '@/client'
import EmptyPanel from '../EmptyPanel.vue'
import WarehouseItemEditableRow from './WarehouseItemEditableRow.vue'

defineEmits<{
  (e: 'dissolveItem', itemId: number): void
  (e: 'removeItem', itemId: number, amount: number): void
  (e: 'addItem'): void
  (e: 'packaged', item: WarehouseItemSchema, items: WarehouseItemSchema[]): void
  (e: 'moved', itemId: number, location: WarehouseLocationSchema): void
}>()
defineProps<{ readonly?: boolean; allowMove?: boolean }>()
const items = defineModel<Array<WarehouseItemSchema>>('items', { default: [] })
</script>
