<template>
  <div v-if="order" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-between flex-wrap">
      <q-breadcrumbs class="mb-5 flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Výdejky" :to="{ name: 'warehouseOutboundOrders' }" />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <div class="flex flex-col items-end gap-3 flex-1">
        <OrderProgress :order="order" class="flex-1 h-6 w-full" />
      </div>
    </div>

    <div class="mb-2 flex gap-2 justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">VÝDEJKA</span>
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <div class="min-w-xs flex flex-col gap-2 items-start">
          <OutboundWarehouseOrderStateBadge :state="order.state" />
        </div>
      </div>
    </div>

    <div class="flex gap-2">
      <CustomerCard :customer="order.order.customer" title="Odběratel" class="flex-[3]" />
      <ForegroundPanel class="flex-1 flex flex-col justify-center items-center gap-2">
        <span class="text-gray-5 text-2xs uppercase">Objednávka</span>
        <a
          class="link text-lg"
          @click="$router.push({ name: 'outgoingOrderDetail', params: { code: order.order.code } })"
        >
          {{ order.order.code }}
        </a>
      </ForegroundPanel>
    </div>

    <ForegroundPanel>
      <span class="text-gray-5 text-xs">Pohyby</span>
      <TransitionGroup name="list" tag="div" class="flex mt-2">
        <WarehouseMovementItem
          v-for="(movement, index) in movements"
          :key="index"
          :index="index + 1"
          :movement="movement"
        />
        <q-item v-if="movements.length === 0">
          <q-item-section>
            <q-item-label caption>Žádné pohyby nebyly zaznamenány.</q-item-label>
          </q-item-section>
        </q-item>
      </TransitionGroup>
    </ForegroundPanel>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> VÝDEJKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type OutboundWarehouseOrderSchema,
  warehouseApiRoutesWarehouseGetOutboundWarehouseOrder,
} from '@/client'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import OrderProgress from '@/components/OrderProgress.vue'
import OutboundWarehouseOrderStateBadge from '@/components/putaway/OutboundWarehouseOrderStateBadge.vue'
import WarehouseMovementItem from '@/components/warehouse/WarehouseMovementItem.vue'
import { useApi } from '@/composables/use-api'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()
const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetOutboundWarehouseOrder({
  path: { code: props.code },
})
const data = onResponse(response)

const order = ref<OutboundWarehouseOrderSchema>()
if (data) {
  order.value = data.data
}

const movements = computed(() => order.value?.movements ?? [])
</script>
