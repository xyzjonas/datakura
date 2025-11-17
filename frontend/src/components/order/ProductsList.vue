<template>
  <div class="draggable-container">
    <TransitionGroup>
      <ForegroundPanel
        v-for="(item, index) in items"
        :key="item.product.code"
        :class="{ dragging: draggingIndex === index, 'drag-over': dragOverIndex === index }"
        draggable="true"
        @dragstart="handleDragStart($event, index)"
        @dragend="handleDragEnd"
        @dragover="handleDragOver($event, index)"
        @dragleave="handleDragLeave"
        @drop="handleDrop($event, index)"
      >
        <div class="drag-handle">
          <q-icon name="sym_o_drag_indicator" size="1rem" />
        </div>
        <ProductRow v-model:item="items[index]" :currency="currency"></ProductRow>
      </ForegroundPanel>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import type { IncomingOrderItemSchema } from '@/client'
import { ref } from 'vue'
import ProductRow from './ProductRow.vue'
import ForegroundPanel from '../ForegroundPanel.vue'

defineProps<{ currency: string }>()
const items = defineModel<Array<IncomingOrderItemSchema>>('items', { default: [] })
const draggingIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// Watch for external changes to items
// watch(
//   items,
//   (newItems) => {
//     items.value = [...newItems]
//   },
//   { deep: true },
// )

// eslint-disable-next-line
const handleDragStart = (event: any, index: number) => {
  if (!event.dataTransfer || !event.target) {
    return
  }
  draggingIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/html', event.target.innerHTML)

  // Make the dragged element slightly transparent
  event.target.style.opacity = '0.5'
}

// eslint-disable-next-line
const handleDragEnd = (event: any) => {
  event.target.style.opacity = '1'
  draggingIndex.value = null
  dragOverIndex.value = null
}

// eslint-disable-next-line
const handleDragOver = (event: any, index: number | null) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'

  if (draggingIndex.value !== null && draggingIndex.value !== index) {
    dragOverIndex.value = index
  }
}

const handleDragLeave = () => {
  dragOverIndex.value = null
}

const handleDrop = (event: Event, dropIndex: number) => {
  event.preventDefault()

  if (draggingIndex.value === null || draggingIndex.value === dropIndex) {
    return
  }

  const newItems = [...items.value]
  const draggedItem = newItems[draggingIndex.value]

  // Remove the dragged item from its original position
  newItems.splice(draggingIndex.value, 1)

  // Insert it at the new position
  newItems.splice(dropIndex, 0, draggedItem)

  items.value = newItems
  dragOverIndex.value = null

  // Emit the updated order
  // emit('update:items', newItems)
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
