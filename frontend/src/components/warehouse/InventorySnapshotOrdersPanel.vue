<template>
  <OrderItemsHeader :title="title" class="!mb-0">
    <template #actions>
      <div v-if="totals.length" class="flex flex-col items-end gap-1">
        <div class="text-xs uppercase tracking-wide text-muted">{{ totalLabel }}</div>
        <strong v-for="row in totals" :key="row.currency" class="text-lg text-primary">
          {{ formatMoney(row.value, row.currency) }}
        </strong>
      </div>
      <span v-else class="text-sm text-muted">—</span>
    </template>

    <div v-if="orders.length" class="flex flex-col divide-y">
      <div
        v-for="order in orders"
        :key="order.id"
        class="grid items-center gap-3 px-4 py-3 md:grid-cols-[1fr_1fr_2fr_auto]"
      >
        <router-link
          :to="{ name: routeName, params: { code: order.code } }"
          class="font-semibold text-primary"
        >
          {{ order.code }}
        </router-link>
        <div class="min-w-0">
          <div class="truncate text-sm">{{ order.counterparty_name || '—' }}</div>
          <div class="text-xs text-gray-5">{{ formatClosedAt(order.closed_at) }}</div>
        </div>
        <div class="truncate text-sm text-gray-6">{{ order.description || '—' }}</div>
        <div class="text-right text-sm font-semibold">
          {{ formatMoney(order.total_value, order.currency) }}
        </div>
      </div>
    </div>

    <div v-else class="px-4 py-6 text-center text-sm text-gray-5">{{ emptyLabel }}</div>
  </OrderItemsHeader>
</template>

<script setup lang="ts">
import type { InventorySnapshotCurrencyTotal, InventorySnapshotOrderSchema } from '@/client'
import OrderItemsHeader from '@/components/order/OrderItemsHeader.vue'
import { formatCurrency } from '@/utils/format-number'

defineProps<{
  title: string
  totalLabel: string
  totals: InventorySnapshotCurrencyTotal[]
  orders: InventorySnapshotOrderSchema[]
  routeName: 'inboundOrderDetail' | 'warehouseOutboundOrderDetail'
  emptyLabel: string
}>()

const formatMoney = (value: string, currency: string) => formatCurrency(value, currency)

const formatClosedAt = (value: string) => new Date(value).toLocaleString('cs-CZ')
</script>
