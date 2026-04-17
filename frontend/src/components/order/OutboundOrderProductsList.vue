<template>
  <div class="draggable-container" v-if="items.length > 0">
    <TransitionGroup>
      <ForegroundPanel
        v-for="(item, index) in items"
        :key="item.product.code"
        :class="{ dragging: draggingIndex === index, 'drag-over': dragOverIndex === index }"
        :draggable="!readonly"
        @dragstart="handleDragStart($event, index)"
        @dragend="handleDragEnd"
        @dragover="handleDragOver($event, index)"
        @dragleave="handleDragLeave"
        @drop="handleDrop($event, index)"
      >
        <div :class="!readonly ? 'drag-handle' : ''">
          <q-icon :name="readonly ? 'sym_o_check_small' : 'sym_o_drag_indicator'" size="1rem" />
        </div>
        <OutboundOrderItemRow
          v-model:item="items[index]"
          :readonly="readonly"
          :currency="currency"
          :order-code="orderCode"
          :customer-code="customerCode"
          @remove="emit('removeItem', item.product.code)"
        />
      </ForegroundPanel>
    </TransitionGroup>
  </div>
  <EmptyPanel v-else icon="sym_o_apps_outage">
    <div class="flex flex-col gap-2 items-start py-10">
      <h3 class="uppercase">Žádné položky</h3>
      <span class="link uppercase" @click="$emit('addItem')">přidat položku</span>
    </div>
  </EmptyPanel>
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import { ref } from 'vue'
import EmptyPanel from '../EmptyPanel.vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import OutboundOrderItemRow from './OutboundOrderItemRow.vue'

const emit = defineEmits<{
  (e: 'removeItem', productCode: string): void
  (e: 'addItem'): void
  (e: 'reorderItems', items: OutboundOrderItemSchema[]): void
}>()

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  customerCode?: string
}>()

const items = defineModel<OutboundOrderItemSchema[]>('items', {
  default: [],
})

const draggingIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

const handleDragStart = (event: DragEvent, index: number) => {
  if (!event.dataTransfer) {
    return
  }
  draggingIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
}

const handleDragEnd = () => {
  draggingIndex.value = null
  dragOverIndex.value = null
}

const handleDragOver = (event: DragEvent, index: number | null) => {
  event.preventDefault()
  if (draggingIndex.value !== null && draggingIndex.value !== index) {
    dragOverIndex.value = index
  }
}

const handleDragLeave = () => {
  dragOverIndex.value = null
}

const handleDrop = (event: DragEvent, dropIndex: number) => {
  event.preventDefault()
  if (draggingIndex.value === null || draggingIndex.value === dropIndex) {
    return
  }

  const newItems = [...items.value]
  const draggedItem = newItems[draggingIndex.value]
  newItems.splice(draggingIndex.value, 1)
  newItems.splice(dropIndex, 0, draggedItem)
  items.value = newItems
  dragOverIndex.value = null
  emit('reorderItems', newItems)
}
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

.dragging {
  opacity: 0.5;
}

.drag-over {
  border-top: 3px solid $primary;
  padding-top: 15px;
}

.drag-handle {
  display: flex;
  align-items: center;
  color: #9ca3af;
}
</style>
