<template>
  <q-chip square>
    <transition :duration="0" name="fade" mode="out-in">
      <q-spinner v-if="loading" class="w-12"></q-spinner>
      <div v-else class="flex items-center justify-center justify-around gap-2 min-w-30">
        <div class="flex flex-col items-end line-height-snug">
          <span class="text-[10px]">volných</span>
          <span class="line-height-none">{{ availableAmount }}</span>
        </div>
        <q-separator vertical />
        <div class="flex flex-col items-start line-height-snug">
          <span class="text-[10px]">skladem</span>
          <span class="line-height-none">{{ totalAmount }}</span>
        </div>
      </div>
    </transition>
  </q-chip>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProductWarehouseAvailability } from '@/client'
import { onMounted, ref } from 'vue'

const props = defineProps<{ productCode: string }>()

const loading = ref(true)
const totalAmount = ref(0)
const availableAmount = ref(0)

const fetch = async () => {
  const result = await warehouseApiRoutesProductGetProductWarehouseAvailability({
    path: { product_code: props.productCode },
  })
  if (result.data?.success && result.data?.data) {
    totalAmount.value = result.data.data.total_amount
    availableAmount.value = result.data.data.available_amount
  }
  loading.value = false
  // setTimeout(() => (loading.value = false), Math.random() * 300)
}

onMounted(fetch)
</script>

<style lang="scss" scoped></style>
