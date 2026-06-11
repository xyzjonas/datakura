<template>
  <router-link
    :to="{ name: 'productDetail', params: { productCode: product.code } }"
    :class="props.class"
    >{{ product.name }}</router-link
  >
</template>

<script setup lang="ts">
import type { ProductSchema } from '@/client'

const props = withDefaults(
  defineProps<{
    product: Pick<ProductSchema, 'code' | 'name'>
    class?: string
  }>(),
  {
    class: 'link',
  },
)
</script>

<style lang="scss" scoped></style>
