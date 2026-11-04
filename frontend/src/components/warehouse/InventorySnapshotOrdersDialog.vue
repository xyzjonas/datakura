<template>
  <q-dialog v-model="show">
    <q-card class="w-3xl max-w-full">
      <div class="flex items-center justify-between p-4">
        <div>
          <h2>{{ title }}</h2>
          <div class="mt-1 text-sm text-gray-6">{{ subtitle }}</div>
        </div>
        <q-btn flat round icon="close" v-close-popup />
      </div>
      <q-separator />

      <div v-if="orders.length" class="flex max-h-[60vh] flex-col divide-y overflow-auto">
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
            {{ formatCurrency(order.total_value, order.currency) }}
          </div>
        </div>
      </div>

      <div v-else class="px-4 py-8 text-center text-sm text-gray-5">{{ emptyLabel }}</div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { InventorySnapshotOrderSchema } from '@/client'
import { formatCurrency } from '@/utils/format-number'

const show = defineModel<boolean>('show', { default: false })

defineProps<{
  title: string
  subtitle: string
  orders: InventorySnapshotOrderSchema[]
  routeName: 'inboundOrderDetail' | 'warehouseOutboundOrderDetail'
  emptyLabel: string
}>()

const formatClosedAt = (value: string) => new Date(value).toLocaleString('cs-CZ')
</script>
