<template>
  <OrderItemsList
    v-model:items="items"
    :readonly="readonly"
    columns-class="grid-cols-4"
    @add-item="emit('addItem')"
    @reorder-item="(itemIndex, newIndex) => emit('reorderItem', itemIndex, newIndex)"
  >
    <template #header>
      <div>Množství</div>
      <div>Nákupní cena</div>
      <div>Celkem</div>
      <div>Akce</div>
    </template>
    <template #row="{ item, index }">
      <InboundOrderItemRowCompact
        v-model:item="items[index]"
        :readonly="readonly"
        :currency="currency"
        :order-code="orderCode"
        @remove="emit('removeItem', item.index)"
      />
    </template>
  </OrderItemsList>
</template>

<script setup lang="ts">
import type { InboundOrderItemSchema } from '@/client'
import InboundOrderItemRowCompact from './InboundOrderItemRowCompact.vue'
import OrderItemsList from './OrderItemsList.vue'

const emit = defineEmits<{
  (e: 'removeItem', itemIndex: number): void
  (e: 'addItem'): void
  (e: 'reorderItem', itemIndex: number, newIndex: number): void
}>()

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
}>()

const items = defineModel<InboundOrderItemSchema[]>('items', { default: [] })
</script>
