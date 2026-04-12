<template>
  <div @click="showDialog = true">
    <q-chip square class="cursor-pointer">
      <transition :duration="0" name="fade" mode="out-in">
        <q-spinner v-if="loading" class="w-12"></q-spinner>
        <div v-else class="flex items-center justify-center justify-around gap-2">
          <div class="flex flex-col items-end line-height-snug">
            <span class="text-[10px]">volných</span>
            <span class="line-height-none">{{ availableAmount }}</span>
          </div>
          <q-separator vertical />
          <div class="flex flex-col items-center line-height-snug">
            <span class="text-[10px]">skladem</span>
            <span class="line-height-none">{{ totalAmount }}</span>
          </div>
          <q-separator vertical />
          <div class="flex flex-col items-start line-height-snug">
            <span class="text-[10px]">objednáno</span>
            <span class="line-height-none">{{ incomingAmount }}</span>
          </div>
        </div>
      </transition>
    </q-chip>

    <ProductAvailabilityDialog v-model="showDialog" :product-code="productCode" />
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProductWarehouseAvailability } from '@/client'
import { useApi } from '@/composables/use-api'
import { onMounted, ref } from 'vue'
import ProductAvailabilityDialog from './ProductAvailabilityDialog.vue'

const props = defineProps<{ productCode: string }>()

const loading = ref(true)
const totalAmount = ref(0)
const availableAmount = ref(0)
const incomingAmount = ref(0)
const showDialog = ref(false)

const { onResponse } = useApi()

const fetch = async () => {
  const response = await warehouseApiRoutesProductGetProductWarehouseAvailability({
    path: { product_code: props.productCode },
  })
  const data = onResponse(response)
  if (data) {
    totalAmount.value = +data.data.total_amount
    availableAmount.value = +data.data.available_amount
    incomingAmount.value = +data.data.incoming_amount
  }
  loading.value = false
}

onMounted(fetch)
</script>

<style lang="scss" scoped></style>
