<template>
  <q-dialog v-model="show">
    <q-card class="flex flex-col" style="width: 600px; max-width: 95vw">
      <q-card-section class="flex items-start gap-3 pb-3">
        <div class="flex-1 min-w-0">
          <router-link
            :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
            class="link text-xl font-semibold leading-tight"
            >{{ item.product.name }}</router-link
          >
          <div class="text-xs text-gray-5 mt-0.5">{{ item.product.code }}</div>
          <ProductAvailability :product-code="item.product.code" class="mt-1 translate-x-[-5px]" />
        </div>
        <q-btn flat round dense icon="sym_o_close" v-close-popup class="mt-0.5" />
      </q-card-section>

      <q-separator />

      <q-card-section class="flex flex-col gap-4 pt-5 overflow-auto">
        <q-input
          v-model.number="item.amount"
          outlined
          label="Množství"
          :rules="[rules.max99999]"
          hide-bottom-space
          :debounce="500"
          @update:model-value="update('amount')"
        >
          <template #append>
            <span class="text-xs text-gray-6">{{ item.product.unit }}</span>
          </template>
        </q-input>

        <q-separator />

        <q-input
          v-model.number="unitPrice"
          dense
          outlined
          label="Nákupní cena"
          :debounce="500"
          @update:model-value="update('unit')"
        >
          <template #append>
            <span class="text-xs text-gray-6">{{ currency }} / {{ item.product.unit }}</span>
          </template>
        </q-input>
        <q-input
          v-model.number="totalPrice"
          dense
          outlined
          label="Celková cena"
          :rules="[rules.max99999]"
          hide-bottom-space
          :debounce="500"
          @update:model-value="update('total')"
        >
          <template #append>
            <span class="text-xs text-gray-6">{{ currency }}</span>
          </template>
        </q-input>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder,
  type InboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { round } from '@/utils/round'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'
import ProductAvailability from '../product/ProductAvailability.vue'

const $q = useQuasar()
const { onResponse } = useApi()

const props = defineProps<{
  currency: string
  orderCode: string
}>()

const show = defineModel<boolean>('show', { default: false })
const item = defineModel<InboundOrderItemSchema>('item', { required: true })

const totalPrice = ref(round(item.value.unit_price * item.value.amount))
const unitPrice = ref(round(item.value.unit_price))

watch(show, (visible) => {
  if (visible) {
    totalPrice.value = round(item.value.unit_price * item.value.amount)
    unitPrice.value = round(item.value.unit_price)
  }
})

const update = async (changedField: 'amount' | 'unit' | 'total') => {
  if (changedField === 'total') {
    unitPrice.value = item.value.amount ? round(totalPrice.value / item.value.amount) : 0
  } else {
    totalPrice.value = round(item.value.amount * round(unitPrice.value))
  }

  const res = await warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder({
    path: { order_code: props.orderCode, item_index: item.value.index },
    body: {
      product_code: item.value.product.code,
      product_name: item.value.product.name,
      amount: item.value.amount,
      total_price: totalPrice.value,
      unit_price: unitPrice.value,
    },
  })

  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
    totalPrice.value = data.data.total_price
    unitPrice.value = data.data.unit_price
    $q.notify({ type: 'positive', message: 'Položka aktualizována' })
  }
}
</script>
