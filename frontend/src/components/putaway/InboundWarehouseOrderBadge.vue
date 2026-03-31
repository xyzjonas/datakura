<template>
  <div class="flex flex-col">
    <span class="text-gray-5 text-2xs uppercase">{{ label }}</span>
    <div class="flex items-center gap-2">
      <a class="link text-lg" @click="goToWarehouseOrderIn(order.code)">{{ order.code }} </a>
      <InboundWarehouseOrderStateBadge :state="order.state"></InboundWarehouseOrderStateBadge>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { InboundWarehouseOrderBaseSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import InboundWarehouseOrderStateBadge from './InboundWarehouseOrderStateBadge.vue'

const { goToWarehouseOrderIn } = useAppRouter()

withDefaults(
  defineProps<{
    order: InboundWarehouseOrderBaseSchema
    label?: string
  }>(),
  {
    label: 'Příjemka',
  },
)
</script>

<style lang="scss" scoped></style>
