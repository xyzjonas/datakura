<template>
  <div v-if="cardLayout" class="flex flex-col gap-2" data-test="order-item-cards">
    <template v-if="items.length > 0">
      <slot
        v-for="(item, index) in items"
        :key="item.index"
        name="row"
        :item="item"
        :index="index"
      />
    </template>
    <EmptyPanel v-else icon="sym_o_apps_outage">
      <div class="flex flex-col gap-2 items-start py-10">
        <h3 class="uppercase">Žádné položky</h3>
        <span v-if="!readonly" class="link uppercase" @click="$emit('addItem')"
          >přidat položku</span
        >
      </div>
    </EmptyPanel>
  </div>
  <template v-else>
    <div class="flex items-center flex-nowrap px-5 text-muted">
      <div class="w-16">#</div>
      <div class="w-xs">{{ productLabel }}</div>
      <div :class="['grid flex-1 text-right', columnsClass]">
        <slot name="header" />
      </div>
    </div>
    <div class="draggable-container" v-if="items.length > 0">
      <TransitionGroup>
        <ForegroundPanel
          v-for="(item, index) in items"
          :key="item.index"
          :class="[
            'w-full',
            draggingIndex === index ? 'dragging' : '',
            dragOverIndex === index ? 'drag-over' : '',
          ]"
          :draggable="draggable"
          @dragstart="handleDragStart($event, index)"
          @dragend="handleDragEnd"
          @dragover="handleDragOver($event, index)"
          @dragleave="handleDragLeave"
          @drop="handleDrop($event, index)"
          :body-class="['flex w-full items-center gap-2 flex-nowrap']"
        >
          <div :class="draggable ? 'drag-handle' : ''">
            <q-icon :name="draggable ? 'sym_o_drag_indicator' : 'sym_o_check_small'" size="1rem" />
          </div>
          <slot name="row" :item="item" :index="index" />
        </ForegroundPanel>
      </TransitionGroup>
    </div>
    <EmptyPanel v-else icon="sym_o_apps_outage">
      <div class="flex flex-col gap-2 items-start py-10">
        <h3 class="uppercase">Žádné položky</h3>
        <span v-if="!readonly" class="link uppercase" @click="$emit('addItem')"
          >přidat položku</span
        >
      </div>
    </EmptyPanel>
  </template>
</template>

<script setup lang="ts" generic="T extends { index: number }">
import { computed, ref } from 'vue'
import { useOrderItemCardLayout } from '@/composables/use-order-item-card-layout'
import EmptyPanel from '../EmptyPanel.vue'
import ForegroundPanel from '../ForegroundPanel.vue'

const emit = defineEmits<{
  (e: 'addItem'): void
  (e: 'reorderItem', itemIndex: number, newIndex: number): void
}>()

const props = withDefaults(
  defineProps<{
    readonly?: boolean
    /** Allow drag & drop reordering (when not readonly). */
    reorderable?: boolean
    /** Label of the product column. */
    productLabel?: string
    /** UnoCSS grid-cols class for the header / row columns. */
    columnsClass?: string
  }>(),
  { reorderable: true, productLabel: 'Produkt' },
)

const draggable = computed(() => !props.readonly && props.reorderable)

const cardLayout = useOrderItemCardLayout()

const items = defineModel<T[]>('items', {
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
  emit('reorderItem', draggedItem.index, dropIndex)
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
