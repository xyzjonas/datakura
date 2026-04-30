<template>
  <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between flex-1 py-1">
    <div class="flex flex-col gap-2">
      <div class="flex items-center gap-2">
        <a
          class="link"
          @click="
            $router.push({ name: 'productDetail', params: { productCode: item.product.code } })
          "
        >
          {{ item.product.name }}
        </a>
        <q-badge :color="item.pending ? 'warning' : 'positive'">
          {{ item.pending ? 'K VYCHYSTÁNÍ' : 'PŘIŘAZENO' }}
        </q-badge>
      </div>

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
        <span>
          {{ item.warehouse_item.location.warehouse_name }} /
          {{ item.warehouse_item.location.code }}
        </span>
        <WarehouseItemTypeBadgeGroup :item="item.warehouse_item" />
        <WarehouseItemLink :item-id="item.warehouse_item.id" />
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
    @confirm="assignWarehouseItem"
  />

  <OffloadItemToChildOrderDialog
    v-model:show="offloadDialog"
    :item="offloadItem"
    @confirm="offload"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem,
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

const props = defineProps<{
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

const assignWarehouseItem = async (warehouseItemId: number) => {
  const response = await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
    path: { code: props.warehouseOrderCode, item_id: props.item.id },
    body: { warehouse_item_id: warehouseItemId },
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
