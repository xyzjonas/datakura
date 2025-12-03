<template>
  <div v-if="warehouseOrder">{{ warehouseOrder.code }}</div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetInboundWarehouseOrder,
  type WarehouseOrderSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'

const props = defineProps<{ code: string }>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetInboundWarehouseOrder({
  path: { code: props.code },
})
const data = onResponse(response)

const warehouseOrder = ref<WarehouseOrderSchema>()
if (data) {
  warehouseOrder.value = data.data
}
</script>

<style lang="scss" scoped></style>
