<template>
  <ForegroundPanel>
    <q-card flat class="h-full bg-transparent">
      <q-card-section class="flex items-center justify-between gap-2">
        <a
          class="link font-semibold text-lg"
          @click="
            $router.push({
              name: 'warehouseInboundOrderDetail',
              params: { code: order.code },
            })
          "
        >
          {{ order.code }}
        </a>
        <InboundWarehouseOrderStateBadge :state="order.state" />
      </q-card-section>

      <q-separator dark />

      <q-card-section class="space-y-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Objednávka</span>
          <a
            class="link truncate text-right max-w-40"
            @click="
              $router.push({
                name: 'inboundOrderDetail',
                params: { code: order.order.code },
              })
            "
          >
            {{ order.order.code }}
          </a>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Dodavatel</span>
          <span class="truncate text-right max-w-40">{{ order.order.supplier?.name ?? '-' }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Naskladněno</span>
          <div class="w-36">
            <OrderProgress :order="order" height="14px" />
          </div>
        </div>
      </q-card-section>
    </q-card>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { InboundWarehouseOrderSchema } from '@/client'
import ForegroundPanel from '../ForegroundPanel.vue'
import OrderProgress from '../OrderProgress.vue'
import InboundWarehouseOrderStateBadge from './InboundWarehouseOrderStateBadge.vue'

defineProps<{
  order: InboundWarehouseOrderSchema
}>()
</script>

<style lang="scss" scoped></style>
