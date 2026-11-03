<template>
  <OrderItemsList
    v-model:items="items"
    :readonly="readonly"
    columns-class="grid-cols-6"
    @add-item="emit('addItem')"
    @reorder-item="(itemIndex, newIndex) => emit('reorderItem', itemIndex, newIndex)"
  >
    <template #header>
      <div>Množství</div>
      <div>Nákupní cena</div>
      <div>Prodejní cena</div>
      <div>Marže</div>
      <div>Celkem</div>
      <div>Akce</div>
    </template>
    <template #row="{ item, index }">
      <OutboundOrderItemRowCompact
        v-model:item="items[index]"
        :readonly="readonly"
        :currency="currency"
        :order-code="orderCode"
        :customer-code="customerCode"
        @remove="emit('removeItem', item.index)"
      />
    </template>
  </OrderItemsList>
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import OrderItemsList from './OrderItemsList.vue'
import OutboundOrderItemRowCompact from './OutboundOrderItemRowCompact.vue'

const emit = defineEmits<{
  (e: 'removeItem', itemIndex: number): void
  (e: 'addItem'): void
  (e: 'reorderItem', itemIndex: number, newIndex: number): void
}>()

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  customerCode?: string
}>()

const items = defineModel<OutboundOrderItemSchema[]>('items', { default: [] })
</script>
