<template>
  <ForegroundPanel no-padding class="p-2">
    <q-card flat class="h-full bg-transparent">
      <q-card-section class="flex items-center justify-between gap-2">
        <div class="min-w-0">
          <span class="flex items-center gap-1 whitespace-nowrap text-sm">
            <ProductTypeIcon :type="product.type" />
            {{ product.type }}
          </span>
          <a
            class="link block truncate font-semibold text-lg text-wrap"
            @click="
              $router.push({
                name: 'productDetail',
                params: { productCode: product.code },
              })
            "
          >
            {{ product.name }}
          </a>
          <div class="text-sm text-gray-5">{{ product.code }}</div>
        </div>
      </q-card-section>

      <q-separator dark />

      <q-card-section class="space-y-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Skupina</span>
          <span class="truncate text-right max-w-40">{{ product.group ?? '-' }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Nákupní cena</span>
          <span>{{ formatPrice(product.purchase_price) }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-gray-4">Prodejní cena</span>
          <span class="font-bold">{{ formatPrice(product.base_price) }}</span>
        </div>
      </q-card-section>
    </q-card>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { ProductSchema } from '@/client'
import ForegroundPanel from '../ForegroundPanel.vue'
import ProductTypeIcon from './ProductTypeIcon.vue'

const props = defineProps<{ product: ProductSchema }>()

const formatPrice = (value: number) => {
  return value ? `${value} ${props.product.currency}` : '-'
}
</script>

<style lang="scss" scoped></style>
