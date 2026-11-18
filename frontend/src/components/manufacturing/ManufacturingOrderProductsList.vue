<template>
  <OrderItemsList
    v-model:items="items"
    :readonly="readonly"
    :reorderable="false"
    product-label="Vstupní produkt"
    columns-class="grid-cols-4"
    @add-item="emit('addItem')"
  >
    <template #header>
      <div>Množství (vstup)</div>
      <div>Výstupní produkt</div>
      <div>Množství (výstup)</div>
      <div>Akce</div>
    </template>
    <template #row="{ item }">
      <ManufacturingOrderItemRowCompact
        :item="item"
        :readonly="readonly"
        @edit="emit('editItem', item)"
        @remove="emit('removeItem', item.id)"
      />
    </template>
  </OrderItemsList>
</template>

<script setup lang="ts">
import type { ManufacturingOrderItemSchema } from '@/client'
import OrderItemsList from '@/components/order/OrderItemsList.vue'
import ManufacturingOrderItemRowCompact from './ManufacturingOrderItemRowCompact.vue'

const emit = defineEmits<{
  (e: 'removeItem', itemId: number): void
  (e: 'editItem', item: ManufacturingOrderItemSchema): void
  (e: 'addItem'): void
}>()

defineProps<{ readonly?: boolean }>()

const items = defineModel<ManufacturingOrderItemSchema[]>('items', { default: [] })
</script>
