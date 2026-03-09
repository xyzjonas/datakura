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
            dense
            flat
            round
            size="10px"
            icon="sym_o_open_in_new"
            :to="{ name: 'warehouseItemDetail', params: { itemId: item.id } }"
          >
            <q-tooltip :offset="[0, 10]">Detail skladové položky</q-tooltip>
          </q-btn>
        </div>
        <div class="mb-2">
          <BarcodeElement
            v-if="item.primary_barcode"
            :barcode="item.primary_barcode"
            :width="1.6"
            text-align="left"
          />
          <span v-else class="text-gray-5 font-mono text-xs bg-gray-2 px-2 py-1 rounded">
            Není evidováno
          </span>
        </div>
        <div class="flex gap-2">
          <q-badge class="py-1" :color="item.location.is_putaway ? 'accent' : 'positive'">{{
            item.location.is_putaway ? 'Příjem' : 'hotovo'
          }}</q-badge>
          <q-badge class="py-1" :color="item.location.is_putaway ? 'gray' : 'positive'">{{
            item.location.code
          }}</q-badge>
          <WarehouseItemTypeBadgeGroup :item="item" />
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
      </div>
      <q-separator vertical class="mx-8" inset />
      <WarehouseItemAmountBadge :item="item" />
    </div>
    <InboundWarehouseOrderTrackDialog
      v-model:show="setItemTrackingDialog"
      :item="item"
      :tracking-type-in="trackingType"
      @packaged="(items) => $emit('packaged', items)"
    />
    <InboundWarehouseOrderRemoveItemDialog
      v-model:show="removeItemDialog"
      :item="item"
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
      :item="item"
      @confirm="(location) => $emit('moved', location)"
    />
  </div>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema, WarehouseLocationSchema } from '@/client'
import { computed, ref } from 'vue'
import BarcodeElement from '../BarcodeElement.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemTypeBadgeGroup from '../warehouse/WarehouseItemTypeBadgeGroup.vue'
import InboundWarehouseOrderRemoveItemDialog from './InboundWarehouseOrderRemoveItemDialog.vue'
import InboundWarehouseOrderTrackDialog, {
  type TrackingType,
} from './InboundWarehouseOrderTrackDialog.vue'
import LocationSelectionDialog from './LocationSelectionDialog.vue'

const props = defineProps<{ item: WarehouseItemSchema; allowMove?: boolean; readonly?: boolean }>()
defineEmits<{
  (e: 'dissolveItem'): void
  (e: 'remove', amount: number): void
  (e: 'packaged', items: WarehouseItemSchema[]): void
  (e: 'moved', location: WarehouseLocationSchema): void
}>()

// const item = defineModel<WarehouseItemSchema>('item', { required: true })

const setItemTrackingDialog = ref(false)

const trackingType = computed<TrackingType>(() => {
  if (props.item.package?.type) {
    return 'package'
  }
  return ''
})

const dissolveDialog = ref(false)
const removeItemDialog = ref(false)
const moveDialog = ref(false)

const isRemovable = computed(() => props.item.tracking_level !== 'FUNGIBLE' && !props.readonly)
const isReadyToBeTracked = computed(
  () => props.item.tracking_level === 'FUNGIBLE' && !props.readonly,
)
</script>

<style lang="scss" scoped></style>
