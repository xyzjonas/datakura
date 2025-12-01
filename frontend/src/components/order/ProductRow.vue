<template>
  <div class="flex w-full justify-between">
    <div>
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
      <br />
      <span class="text-xs text-gray-5">{{ item.product.code }}</span>
    </div>
    <div
      class="flex gap-2 flex-1 items-center justify-start lg:justify-end flex-nowrap min-w-[670px]"
    >
      <ProductAvailability :product-code="item.product.code" class="mr-5" />
      <q-input v-model.number="item.amount" dense standout class="max-w-28" label="Počet">
        <template #append>
          <span class="text-xs">{{ item.product.unit }}</span>
        </template>
      </q-input>
      <q-input
        v-model.number="item.unit_price"
        dense
        standout
        class="max-w-40"
        label="Nákupní cena"
      >
        <template #append>
          <span class="text-xs">{{ currency }}</span>
        </template>
      </q-input>
      <q-input
        readonly
        :model-value="totalPrice"
        dense
        standout
        class="max-w-40"
        label="Celková cena"
      >
        <template #append>
          <span class="text-xs">{{ currency }}</span>
        </template>
      </q-input>
      <q-btn icon="sym_o_close_small" color="negative" flat dense></q-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncomingOrderItemSchema } from '@/client'
import { computed } from 'vue'
import ProductAvailability from '../product/ProductAvailability.vue'

defineProps<{ currency: string }>()

const item = defineModel<IncomingOrderItemSchema>('item', { required: true })

const totalPrice = computed(() => item.value.unit_price * item.value.amount)
</script>

<style lang="scss" scoped></style>
