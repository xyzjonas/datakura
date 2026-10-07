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
          {{ item.pending ? 'K NASKLADNĚNÍ' : 'HOTOVO' }}
        </span>
        <router-link :to="{ name: 'productDetail', params: { productCode: item.product.code } }">
          <h5 class="link text-lg">{{ item.product.name }}</h5>
        </router-link>
        <span class="text-muted text-xs">{{ item.product.code }}</span>

        <div class="flex flex-wrap gap-2 items-center">
          <WarehouseItemAmountBadge :item="amountBadgeItem" />
          <TrackingLevelBadge :level="item.tracking_level" />
          <PackageTypeBadge v-if="item.package" :package-type="item.package.type" />
          <BatchBadge v-if="item.batch_barcode" :batch-code="item.batch_barcode" />
          <q-badge v-if="missingWeight" color="negative" class="py-1" data-test="missing-weight">
            <q-icon name="sym_o_warning" class="mr-1" />Chybí hmotnost
          </q-badge>
          <q-badge
            v-if="item.product.customs_declaration_group"
            outline
            color="grey-7"
            class="py-1"
          >
            <q-icon name="sym_o_assured_workload" class="mr-1" />
            {{ item.product.customs_declaration_group }}
          </q-badge>
          <q-badge v-else color="warning" class="py-1" data-test="missing-customs">
            <q-icon name="sym_o_assured_workload" class="mr-1" />CHYBÍ CELNÍ KÓD
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
        </div>

        <div v-if="item.warehouse_item_id" class="text-sm text-gray-6">
          <WarehouseItemLink :item-id="item.warehouse_item_id!" />
        </div>
      </div>
    </div>

    <div class="flex gap-3 items-center self-end lg:self-auto">
      <q-btn
        v-if="isRemovable"
        @click="removeItemDialog = true"
        flat
        dense
        round
        icon="delete"
        color="negative"
      >
        <q-tooltip :offset="[0, 10]">Odstranit položku z příjemky do dobropisu</q-tooltip>
      </q-btn>
      <q-btn
        v-if="isRemovable"
        @click="dissolveDialog = true"
        flat
        dense
        round
        icon="close"
        color="warning"
      >
        <q-tooltip :offset="[0, 10]">Zrušit evidenci položky ⤍ skladem volně</q-tooltip>
      </q-btn>
      <q-btn
        v-if="!props.readonly"
        flat
        dense
        no-caps
        :color="missingWeight ? 'negative' : 'grey-7'"
        icon="sym_o_edit_note"
        label="Korekce"
        data-test="correction-btn"
        @click="correctionDialog = true"
      >
        <q-tooltip :offset="[0, 10]">Doplnit hmotnost a celní kód produktu</q-tooltip>
      </q-btn>
      <q-btn
        v-if="isReadyToBeTracked"
        flat
        no-caps
        dense
        color="primary"
        icon="sym_o_qr_code_scanner"
        label="Evidovat"
        @click="setItemTrackingDialog = true"
      />
      <q-btn
        v-if="allowMove"
        flat
        no-caps
        dense
        color="primary"
        icon="sym_o_move_up"
        label="Přesunout"
        @click="moveDialog = true"
      />
      <q-btn
        v-if="!props.readonly"
        flat
        no-caps
        dense
        color="warning"
        icon="sym_o_move_down"
        label="Do podřízené"
        @click="offloadDialog = true"
      />
    </div>
  </div>
  <ProductCustomsWeightDialog
    v-model:show="correctionDialog"
    :product="item.product"
    @saved="$emit('corrected')"
  />
  <InboundWarehouseOrderTrackDialog
    v-model:show="setItemTrackingDialog"
    :item="asOrderItem"
    :tracking-type-in="trackingType"
    @packaged="(items, batch, trackingType) => $emit('packaged', items, batch, trackingType)"
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
</template>

<script setup lang="ts">
import type {
  BatchSchema,
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
import WarehouseItemLink from '../links/WarehouseItemLink.vue'
import IndexRectangle from '../IndexRectangle.vue'
import ProductCustomsWeightDialog from '../product/ProductCustomsWeightDialog.vue'

const props = defineProps<{
  index: number
  item: InboundWarehouseOrderItemSchema
  allowMove?: boolean
  readonly?: boolean
  warehouseOrderCode?: string
}>()

const emit = defineEmits<{
  (e: 'dissolveItem'): void
  (e: 'remove', amount: number): void
  (
    e: 'packaged',
    items: WarehouseItemSchema[],
    batch: BatchSchema | undefined,
    trackingType: TrackingType,
  ): void
  (e: 'moved', location: WarehouseLocationSchema): void
  (e: 'offloaded'): void
  (e: 'corrected'): void
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
const correctionDialog = ref(false)

const missingWeight = computed(() => props.item.product.unit_weight <= 0)

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
