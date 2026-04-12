<template>
  <q-dialog v-model="show" full-width>
    <product-orders-section :product-code="productCode" />
  </q-dialog>
</template>

<script setup lang="ts">
import ProductOrdersSection from './ProductOrdersSection.vue'

const show = defineModel<boolean>({ default: false })
defineProps<{
  productCode: string
}>()
</script>
