<template>
  <div class="flex w-full gap-5 items-center">
    <!-- <h5 class="text-gray">1</h5> -->
    <div class="flex flex-col gap-2">
      <div class="flex justify-between gap-2">
        <a
          @click="
            $router.push({
              name: 'productDetail',
              params: { productCode: item.product.code },
            })
          "
          class="link mr-5"
          >{{ item.product.name }}</a
        >
        <div class="flex items-center gap-2">
          <q-badge class="py-1" :color="item.location.is_putaway ? 'accent' : 'positive'">{{
            item.location.is_putaway ? 'Příjem' : 'hotovo'
          }}</q-badge>
          <q-badge class="py-1" color="gray">{{ item.location.code }}</q-badge>
          <PackageTypeBadge :package-type="item.package?.type" class="py-1" />
        </div>
      </div>
      <BarcodeElement :barcode="item.code" :width="1.6" text-align="left" />
    </div>
    <span class="flex flex-nowrap items-center ml-auto">
      <WarehouseItemAmountBadge :item="item" />
    </span>
    <div v-if="!readonly" class="h-full">
      <q-btn
        v-if="!trackingType"
        flat
        color="negative"
        label="dobropis"
        icon="sym_o_undo"
        @click="removeItemDialog = true"
      />
      <q-btn
        v-if="!trackingType"
        flat
        color="primary"
        label="evidovat"
        icon-right="sym_o_qr_code_scanner"
        @click="setItemTrackingDialog = true"
      />
      <q-btn v-else flat color="negative" icon-right="sym_o_close" @click="confirmDelete = true" />
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
      v-model:show="confirmDelete"
      title="Zrušit balení/evidenci?"
      @confirm="$emit('dissolveItem')"
    >
      <div>
        Položka ztratí zvolený typ balení a bude nadále v systému evidována pouze jako
        <PackageTypeBadge :package-type="undefined" />.
      </div>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'
import InboundWarehouseOrderTrackDialog, {
  type TrackingType,
} from './InboundWarehouseOrderTrackDialog.vue'
import { computed, ref } from 'vue'
import BarcodeElement from '../BarcodeElement.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import InboundWarehouseOrderRemoveItemDialog from './InboundWarehouseOrderRemoveItemDialog.vue'

defineProps<{ readonly?: boolean }>()
defineEmits<{
  (e: 'dissolveItem'): void
  (e: 'remove', amount: number): void
  (e: 'packaged', items: WarehouseItemSchema[]): void
}>()

const item = defineModel<WarehouseItemSchema>('item', { required: true })

const setItemTrackingDialog = ref(false)

const trackingType = computed<TrackingType>(() => {
  if (item.value.package?.type) {
    return 'package'
  }
  return ''
})

const confirmDelete = ref(false)
const removeItemDialog = ref(false)
</script>

<style lang="scss" scoped></style>
