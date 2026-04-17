<template>
  <div>
    <div class="flex items-center min-h-20 py-1">
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <a
            @click="
              $router.push({
                name: 'productDetail',
                params: { productCode: item.product.code },
              })
            "
            class="link"
            >{{ item.product.name }}</a
          >
          <q-btn
            v-if="item.warehouse_item_id"
            dense
            flat
            round
            size="10px"
            icon="sym_o_open_in_new"
            :to="{ name: 'warehouseItemDetail', params: { itemId: item.warehouse_item_id } }"
          >
            <q-tooltip :offset="[0, 10]">Detail skladové položky</q-tooltip>
          </q-btn>
        </div>
        <div class="flex gap-2">
          <q-badge class="py-1" :color="item.pending ? 'warning' : 'positive'">
            {{ item.pending ? 'K NASKLADNĚNÍ' : 'HOTOVO' }}
          </q-badge>
          <q-badge
            v-if="item.outbound_order_code"
            color="primary"
            class="py-1 cursor-pointer"
            @click="
              $router.push({
                name: 'warehouseOutboundOrderDetail',
                params: { code: item.outbound_order_code },
              })
            "
          >
            VÝDEJKA {{ item.outbound_order_code }}
          </q-badge>
          <TrackingLevelBadge :level="item.tracking_level" />
          <PackageTypeBadge v-if="item.package" :package-type="item.package.type" />
          <BatchBadge v-if="item.batch_barcode" :batch-code="item.batch_barcode" />
        </div>
      </div>
      <div class="light:text-gray-5 dark:text-gray-3 q-gutter-xs ml-auto">
        <q-btn
          v-if="isRemovable"
          @click="removeItemDialog = true"
          size="14px"
          flat
          dense
          round
          icon="delete"
        >
          <q-tooltip :offset="[0, 10]">Odstranit položku z příjemky do dobropisu</q-tooltip>
        </q-btn>
        <q-btn
          v-if="isRemovable"
          @click="dissolveDialog = true"
          size="14px"
          flat
          dense
          round
          icon="close"
        >
          <q-tooltip :offset="[0, 10]">Zrušit evidenci položky ⤍ skladem volně</q-tooltip>
        </q-btn>
        <q-btn
          v-if="isReadyToBeTracked"
          @click="setItemTrackingDialog = true"
          size="14px"
          flat
          dense
          round
          icon="sym_o_qr_code_scanner"
        >
          <q-tooltip :offset="[0, 10]">Evidovat položku</q-tooltip>
        </q-btn>
        <q-btn
          v-if="allowMove"
          @click="moveDialog = true"
          size="14px"
          flat
          dense
          round
          icon="sym_o_move_up"
        >
          <q-tooltip :offset="[0, 10]">Přesunout položku</q-tooltip>
        </q-btn>
        <q-btn
          v-if="!props.readonly"
          @click="offloadDialog = true"
          size="14px"
          flat
          dense
          round
          icon="sym_o_move_down"
        >
          <q-tooltip :offset="[0, 10]">Přesunout do podřízené objednávky</q-tooltip>
        </q-btn>
      </div>
      <q-separator vertical class="mx-8" inset />
      <WarehouseItemAmountBadge :item="amountBadgeItem" class="min-w-30" />
    </div>
    <InboundWarehouseOrderTrackDialog
      v-model:show="setItemTrackingDialog"
      :item="asOrderItem"
      :tracking-type-in="trackingType"
      @packaged="(items) => $emit('packaged', items)"
    />
    <InboundWarehouseOrderRemoveItemDialog
      v-model:show="removeItemDialog"
      :item="asOrderItem"
      @remove="(amount) => $emit('remove', amount)"
    />
    <ConfirmDialog
      v-model:show="dissolveDialog"
      title="Zrušit balení/evidenci?"
      @confirm="$emit('dissolveItem')"
    >
      <div>
        Položka ztratí zvolený typ balení a bude nadále v systému evidována pouze jako
        <PackageTypeBadge :package-type="undefined" />.
      </div>
    </ConfirmDialog>
    <LocationSelectionDialog
      v-model:show="moveDialog"
      :item="asOrderItem"
      @confirm="(location) => $emit('moved', location)"
    />
    <OffloadItemToChildOrderDialog
      v-model:show="offloadDialog"
      :item="asOffloadItem"
      :loading="offloadLoading"
      @confirm="onOffload"
    />
  </div>
</template>

<script setup lang="ts">
import type {
  InboundWarehouseOrderItemSchema,
  WarehouseItemSchema,
  WarehouseLocationSchema,
} from '@/client'
import { warehouseApiRoutesWarehouseOffloadItemsToChildOrder } from '@/client'
import { computed, ref } from 'vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import TrackingLevelBadge from '../warehouse/TrackingLevelBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import InboundWarehouseOrderRemoveItemDialog from './InboundWarehouseOrderRemoveItemDialog.vue'
import InboundWarehouseOrderTrackDialog, {
  type TrackingType,
} from './InboundWarehouseOrderTrackDialog.vue'
import LocationSelectionDialog from './LocationSelectionDialog.vue'
import OffloadItemToChildOrderDialog from './OffloadItemToChildOrderDialog.vue'

const props = defineProps<{
  item: InboundWarehouseOrderItemSchema
  allowMove?: boolean
  readonly?: boolean
  warehouseOrderCode?: string
}>()

const emit = defineEmits<{
  (e: 'dissolveItem'): void
  (e: 'remove', amount: number): void
  (e: 'packaged', items: WarehouseItemSchema[]): void
  (e: 'moved', location: WarehouseLocationSchema): void
  (e: 'offloaded'): void
}>()

const dummyLocation = computed(() => ({
  warehouse_name: '',
  code: props.item.pending ? 'PRIJEM' : 'HOTOVO',
  is_putaway: props.item.pending,
  created: props.item.created,
  changed: props.item.changed,
}))

/** Adapter for dialogs using order item ID (dissolve, track, remove) */
const asOrderItem = computed<WarehouseItemSchema>(() => ({
  id: props.item.id,
  product: props.item.product,
  unit_of_measure: props.item.unit_of_measure,
  amount: Number(props.item.amount),
  tracking_level: props.item.tracking_level,
  package: props.item.package ?? null,
  location: dummyLocation.value,
  batch: null,
  primary_barcode: null,
  inbound_order_code: null,
  created: props.item.created,
  changed: props.item.changed,
}))

/** Adapter for offload dialog — needs warehouse item ID */
const asOffloadItem = computed<WarehouseItemSchema>(() => ({
  ...asOrderItem.value,
  id: props.item.warehouse_item_id ?? props.item.id,
}))

const amountBadgeItem = computed(() => ({
  amount: Number(props.item.amount),
  unit_of_measure: props.item.unit_of_measure,
}))

const setItemTrackingDialog = ref(false)
const dissolveDialog = ref(false)
const removeItemDialog = ref(false)
const moveDialog = ref(false)
const offloadDialog = ref(false)
const offloadLoading = ref(false)

const trackingType = computed<TrackingType>(() => (props.item.package?.type ? 'package' : ''))

const isRemovable = computed(() => props.item.tracking_level !== 'FUNGIBLE' && !props.readonly)
const isReadyToBeTracked = computed(
  () => props.item.tracking_level === 'FUNGIBLE' && !props.readonly,
)

const onOffload = async (itemId: number, amount: number) => {
  if (!props.warehouseOrderCode) return
  offloadLoading.value = true
  try {
    await warehouseApiRoutesWarehouseOffloadItemsToChildOrder({
      path: { code: props.warehouseOrderCode },
      body: { items: [{ item_id: itemId, amount }] },
    })
    emit('offloaded')
  } finally {
    offloadLoading.value = false
  }
}
</script>

<style lang="scss" scoped></style>
