<template>
  <div
    :class="[
      'flex flex-col lg:flex-row lg:items-center lg:justify-between flex-1 py-1 border border-l-5 rounded-sm px-5 py-4 min-h-30',
      item.pending ? 'border-l-orange' : 'border-l-positive',
    ]"
  >
    <div class="flex gap-4 items-start lg:items-center">
      <IndexRectangle :index="index + 1" />
      <div class="flex flex-col gap-1">
      <span :class="['text-xs font-bold', item.pending ? 'text-orange' : 'text-positive']">
        {{ item.pending ? 'K VYCHYSTÁNÍ' : 'PŘIŘAZENO' }}
      </span>
      <router-link :to="{ name: 'productDetail', params: { productCode: item.product.code } }">
        <h5 class="link text-lg">{{ item.product.name }}</h5>
      </router-link>
      <span class="text-muted text-xs">{{ item.product.code }}</span>

      <div class="flex flex-wrap gap-2 items-center">
        <WarehouseItemAmountBadge :item="amountBadgeItem" />
        <PackageTypeBadge
          v-if="item.desired_package_type_name"
          :package-type="item.desired_package_type_name"
        />
        <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
        <q-badge
          v-if="item.warehouse_item?.inbound_order_code"
          color="accent"
          class="py-1 cursor-pointer"
          @click="
            $router.push({
              name: 'warehouseInboundOrderDetail',
              params: { code: item.warehouse_item!.inbound_order_code },
            })
          "
        >
          PŘÍJEMKA {{ item.warehouse_item.inbound_order_code }}
        </q-badge>
      </div>

      <div v-if="item.warehouse_item" class="text-sm text-gray-6 flex flex-wrap gap-3">
        <span v-if="item.warehouse_item.location">
          {{ item.warehouse_item.location.warehouse_name }} /
          {{ item.warehouse_item.location.code }}
        </span>
        <span v-else class="text-gray-4 italic">vychystáno</span>
        <WarehouseItemTypeBadgeGroup :item="item.warehouse_item" />
        <WarehouseItemLink :item-id="item.warehouse_item.id" />
        <span v-if="item.price_at_shipment != null" class="font-medium text-gray-7">
          Cena při výdeji: {{ Number(item.price_at_shipment).toFixed(2) }} CZK
        </span>
      </div>
    </div>
    </div>

    <div class="flex gap-2 items-center self-end lg:self-auto">
      <q-btn
        v-if="item.pending"
        flat
        color="primary"
        icon="sym_o_playlist_add_check"
        label="vybrat položku"
        @click="pickDialog = true"
      />
      <q-btn
        v-if="item.pending"
        flat
        color="warning"
        icon="sym_o_move_down"
        label="do podřízené"
        @click="offloadDialog = true"
      />
    </div>
  </div>

  <OutboundWarehousePickDialog
    v-model:show="pickDialog"
    :warehouse-order-code="warehouseOrderCode"
    :item="item"
    @confirm="reloadOrder"
  />

  <OffloadItemToChildOrderDialog
    v-model:show="offloadDialog"
    :item="offloadItem"
    @confirm="offload"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseOffloadOutboundItemsToChildOrder,
  type OutboundWarehouseOrderItemSchema,
  type OutboundWarehouseOrderSchema,
  type WarehouseItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { computed, ref } from 'vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemTypeBadgeGroup from '../warehouse/WarehouseItemTypeBadgeGroup.vue'
import OffloadItemToChildOrderDialog from './OffloadItemToChildOrderDialog.vue'
import OutboundWarehousePickDialog from './OutboundWarehousePickDialog.vue'
import WarehouseItemLink from '../links/WarehouseItemLink.vue'
import IndexRectangle from '../IndexRectangle.vue'

const props = defineProps<{
  index: number
  warehouseOrderCode: string
  item: OutboundWarehouseOrderItemSchema
}>()

const emit = defineEmits<{
  (e: 'updated', order: OutboundWarehouseOrderSchema): void
}>()

const { onResponse } = useApi()

const pickDialog = ref(false)
const offloadDialog = ref(false)

const amountBadgeItem = computed(() => ({
  amount: Number(props.item.amount),
  unit_of_measure: props.item.unit_of_measure,
}))

const offloadItem = computed<WarehouseItemSchema>(() => ({
  id: props.item.id,
  product: props.item.product,
  unit_of_measure: props.item.unit_of_measure,
  amount: Number(props.item.amount),
  tracking_level: 'FUNGIBLE',
  location: {
    warehouse_name: '',
    code: 'OUTBOUND',
    is_putaway: false,
    created: props.item.created,
    changed: props.item.changed,
  },
  package: null,
  batch: null,
  primary_barcode: null,
  inbound_order_code: null,
  created: props.item.created,
  changed: props.item.changed,
}))

const reloadOrder = async () => {
  // Dialog handles the assignment, just need to reload the order
  const { warehouseApiRoutesWarehouseGetOutboundWarehouseOrder } = await import('@/client')
  const response = await warehouseApiRoutesWarehouseGetOutboundWarehouseOrder({
    path: { code: props.warehouseOrderCode },
  })
  const data = onResponse(response)
  if (data?.data) {
    emit('updated', data.data)
  }
}

const offload = async (itemId: number, amount: number) => {
  const response = await warehouseApiRoutesWarehouseOffloadOutboundItemsToChildOrder({
    path: { code: props.warehouseOrderCode },
    body: { items: [{ item_id: itemId, amount }] },
  })
  const data = onResponse(response)
  if (data?.data) {
    emit('updated', data.data)
  }
}
</script>
