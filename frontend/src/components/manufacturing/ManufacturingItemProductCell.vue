<template>
  <div class="flex flex-col min-w-0">
    <router-link
      :to="{ name: 'productDetail', params: { productCode: product.code } }"
      class="link font-medium leading-tight"
      >{{ product.name }}</router-link
    >
    <div class="text-xs text-gray-5">{{ product.code }}</div>
  </div>
</template>

<script setup lang="ts">
import type { ProductSchema } from '@/client'

defineProps<{ product: Pick<ProductSchema, 'code' | 'name'> }>()
</script>
