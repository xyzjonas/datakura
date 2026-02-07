<template>
  <div class="flex flex-col ml-2 border py-2 px-5 rounded">
    <span class="text-gray-5 text-2xs">VYDANÁ OBJEDNÁVKA</span>
    <div class="flex items-center gap-2">
      <a class="link text-lg" @click="goToOrderIn(order.code)">{{ order.code }} </a>
      <InboundOrderStateBadge :state="order.state"></InboundOrderStateBadge>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { InboundOrderBaseSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import InboundOrderStateBadge from './InboundOrderStateBadge.vue'

defineProps<{ order: InboundOrderBaseSchema }>()

const { goToOrderIn } = useAppRouter()
</script>

<style lang="scss" scoped></style>
