<template>
  <div class="draggable-container" v-if="items.length > 0">
    <TransitionGroup>
      <ForegroundPanel
        v-for="(item, index) in items"
        :key="item.product.code"
        :class="{ dragging: draggingIndex === index, 'drag-over': dragOverIndex === index }"
      >
        <ProductRow
          v-model:item="items[index]"
          :readonly="props.readonly"
          :currency="props.currency"
          :order-code="props.orderCode"
        ></ProductRow>
      </ForegroundPanel>
    </TransitionGroup>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { CreditNoteSupplierItemSchema } from '@/client'
import { ref } from 'vue'
import EmptyPanel from '../EmptyPanel.vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import ProductRow from '../order/ProductRow.vue'

const props = defineProps<{ currency: string; readonly?: boolean; orderCode: string }>()
const items = defineModel<Array<CreditNoteSupplierItemSchema>>('items', {
  default: [],
})
const draggingIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
</script>

<style scoped lang="scss">
.draggable-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.draggable-container > * {
  position: relative;
  cursor: grab;
  transition: all 0.2s ease;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.draggable-container > *:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.dragging {
  opacity: 0.5;
  cursor: grabbing !important;
}

.drag-over {
  border-top: 3px solid $primary;
  padding-top: 15px;
}

.drag-handle {
  display: flex;
  align-items: center;
  color: #9ca3af;
  cursor: grab;
  padding: 4px;
}

.drag-handle:hover {
  color: $primary;
}

.draggable-container > *:active .drag-handle {
  cursor: grabbing;
}
</style>
