<template>
  <ForegroundPanel no-padding class="p-2">
    <q-card flat class="h-full bg-transparent">
      <q-card-section class="flex items-center justify-between gap-2">
        <a
          class="link font-semibold text-lg"
          @click="
            $router.push({
              name: detailRouteName,
              params: { code: order.code },
            })
          "
        >
          {{ order.code }}
        </a>
        <InboundOrderStateBadge :state="order.state" />
      </q-card-section>

      <q-separator dark />

      <q-card-section class="space-y-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Dodavatel</span>
          <span class="text-right truncate max-w-40">{{ order.supplier?.name ?? '-' }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Počet položek</span>
          <span>{{ order.items?.length ?? 0 }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Celková částka</span>
          <span class="font-bold">{{ calculateTotalPrice(order.items) }} {{ order.currency }}</span>
        </div>
      </q-card-section>
    </q-card>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { type InboundOrderSchema } from '@/client'
import { calculateTotalPrice } from '@/utils/total-price'
import InboundOrderStateBadge from './InboundOrderStateBadge.vue'
import ForegroundPanel from '../ForegroundPanel.vue'

defineProps<{
  order: InboundOrderSchema
  detailRouteName: string
}>()
</script>

<style lang="scss" scoped></style>
