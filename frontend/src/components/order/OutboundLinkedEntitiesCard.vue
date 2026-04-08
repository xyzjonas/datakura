<template>
  <div class="flex flex-col gap-2 min-w-80">
    <template v-if="showWarehouseOrders">
      <ForegroundPanel
        v-for="order in warehouseOrdersToRender"
        :key="order.code"
        class="flex-1 flex justify-center items-center"
      >
        <OutboundWarehouseOrderBadge :order="order" />
      </ForegroundPanel>
      <ForegroundPanel
        v-if="warehouseOrdersToRender.length === 0"
        class="flex-1 flex justify-center items-center"
      >
        <span class="text-gray-5">Žádná Výdejka</span>
      </ForegroundPanel>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { OutboundWarehouseOrderBaseSchema } from '@/client'
import type { Optional } from '@/utils/optional'
import { computed } from 'vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import OutboundWarehouseOrderBadge from '../putaway/OutboundWarehouseOrderBadge.vue'

const props = defineProps<{
  showWarehouseOrders?: boolean
  warehouseOrders?: Optional<OutboundWarehouseOrderBaseSchema[]>
}>()

const warehouseOrdersToRender = computed(() => props.warehouseOrders ?? [])
</script>
