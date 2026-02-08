<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-xl">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center gap-2">
          <div class="flex flex-col">
            <span class="text-2xl uppercase">Odstranit položku</span>
            <a class="link" @click="goToProduct(item.product.code)">{{ item.product.name }}</a>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <div class="text-gray-5 mt-3 mb-5">
          Množství
          <span class="flex items-center inline">
            <WarehouseItemAmountBadge :item="item" :amount="amount" />
          </span>
          bude odstraněno z příjemky a zaznamenáno do dobropisu. Pokračujte pokud je zvolená položka
          opravdu reklamována a <strong>NEBUDE</strong> přijata na sklad
        </div>
        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model="amount"
            outlined
            :label="`Množství`"
            :rules="[
              rules.isNumber,
              rules.atLeastOne,
              (val) => val <= item.amount || `K dispozici je maximálně ${item.amount} jednotek`,
            ]"
          >
            <template #append>
              <span class="text-xs">{{ item.unit_of_measure }}</span>
            </template>
          </q-input>
          <div class="px-3">
            <q-slider
              v-model="amount"
              :markers="Math.ceil(item.amount / 10)"
              :min="0"
              :max="item.amount"
              marker-labels
              :step="item.amount > 50 ? 10 : 1"
            ></q-slider>
          </div>

          <div v-if="items.length > 0">
            <WarehouseItemPreviewRow :item="item" :index="0" :amount="amount" />
            <div class="flex w-full justify-center my-2">
              <q-icon name="sym_o_arrow_cool_down" size="20px" />
            </div>
            <WarehouseItemPreviewRow
              v-for="(item, index) in items"
              :index="index"
              :item="item"
              :key="item.product.code"
            />
          </div>

          <q-btn type="submit" unelevated color="primary" label="Odstranit" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingPackagePreview,
  type PackageTypeSchema,
  type WarehouseItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemPreviewRow from './WarehouseItemPreviewRow.vue'

const { onResponse } = useApi()
const { goToProduct } = useAppRouter()

const props = defineProps<{
  item: WarehouseItemSchema
}>()

const amount = ref(props.item.amount)

const selectedPackage = ref<PackageTypeSchema>()

const showDialog = defineModel('show', { default: false })

const items = ref<WarehouseItemSchema[]>([])
const previewItems = async () => {
  if (!selectedPackage.value) {
    return
  }
  const result = await warehouseApiRoutesPackagingPackagePreview({
    body: {
      warehouse_item_id: props.item.id,
      amount: amount.value,
      package_name: selectedPackage.value?.name,
      product_code: props.item.product.code,
    },
  })
  const data = onResponse(result)
  if (data) {
    items.value = data.data
  }
}

watch([selectedPackage, amount], () => {
  if (selectedPackage.value) {
    previewItems()
  } else {
    items.value = []
  }
})

const emit = defineEmits<{
  (e: 'remove', amount: number): void
}>()
const onSubmit = () => {
  showDialog.value = false
  emit('remove', amount.value)
}
</script>
<style lang="css" scoped></style>
