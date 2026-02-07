<template>
  <div class="flex flex-col ml-2 border py-2 px-5 rounded">
    <span class="text-gray-5 text-2xs">PŘÍJEMKA</span>
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

defineProps<{ order: InboundWarehouseOrderBaseSchema }>()
</script>

<style lang="scss" scoped></style>
