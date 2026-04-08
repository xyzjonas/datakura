<template>
  <div class="flex flex-col">
    <span class="text-gray-5 text-2xs uppercase">{{ label }}</span>
    <div class="flex items-center gap-2">
      <a class="link text-lg" @click="goToWarehouseOrderOut(order.code)">{{ order.code }}</a>
      <OutboundWarehouseOrderStateBadge :state="order.state" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { OutboundWarehouseOrderBaseSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import OutboundWarehouseOrderStateBadge from './OutboundWarehouseOrderStateBadge.vue'

const { goToWarehouseOrderOut } = useAppRouter()

withDefaults(
  defineProps<{
    order: OutboundWarehouseOrderBaseSchema
    label?: string
  }>(),
  {
    label: 'Výdejka',
  },
)
</script>
