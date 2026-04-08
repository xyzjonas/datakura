<template>
  <div class="flex w-full justify-between items-center gap-5">
    <IndexRectangle v-if="index" :index="index" />
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
      class="flex gap-3 flex-1 items-center justify-start lg:justify-end flex-nowrap min-w-[670px]"
    >
      <ProductAvailability :product-code="item.product.code" class="mr-5" />
      <q-input
        v-model.number="item.amount"
        :readonly="readonly"
        dense
        outlined
        class="max-w-28"
        label="Počet"
        @update:model-value="update"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ item.product.unit }}</span>
        </template>
      </q-input>
      <q-input
        v-model.number="unitPrice"
        :readonly="isUnitPriceReadonly"
        dense
        outlined
        class="max-w-50"
        label="Nákupní cena"
        @update:model-value="update"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ currency }} / {{ item.product.unit }}</span>
        </template>
      </q-input>
      <q-input
        :readonly="readonly"
        v-model.number="totalPrice"
        @update:model-value="update"
        dense
        outlined
        class="max-w-40"
        label="Celková cena"
        :debounce="500"
      >
        <template #append>
          <span class="text-xs">{{ currency }}</span>
        </template>
      </q-input>
      <q-btn
        v-if="!readonly"
        icon="sym_o_close_small"
        color="negative"
        flat
        dense
        @click="$emit('dissolveItem')"
      ></q-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder,
  warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder,
  type CreditNoteSupplierItemSchema,
  type InboundOrderItemSchema,
  type OutboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { round } from '@/utils/round'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'
import IndexRectangle from '../IndexRectangle.vue'
import ProductAvailability from '../product/ProductAvailability.vue'

const $q = useQuasar()
const { onResponse } = useApi()

const props = defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  orderType: 'inbound' | 'outbound'
}>()
defineEmits<{ (e: 'dissolveItem'): void }>()

const item = defineModel<
  InboundOrderItemSchema | OutboundOrderItemSchema | CreditNoteSupplierItemSchema
>('item', {
  required: true,
})

const totalPrice = ref(round(item.value.unit_price * item.value.amount))
const unitPrice = ref(round(item.value.unit_price))
const derivedUnitPrice = computed(() => {
  if (!item.value.amount) {
    return 0
  }
  if (props.orderType === 'outbound') {
    return round(unitPrice.value)
  }
  return round(totalPrice.value / item.value.amount)
})

const isUnitPriceReadonly = computed(() => props.readonly || props.orderType === 'inbound')

const index = computed(() => (isInboundOrderItem(item.value) ? item.value.index + 1 : undefined))

const isInboundOrderItem = (
  item: InboundOrderItemSchema | CreditNoteSupplierItemSchema,
): item is InboundOrderItemSchema => {
  return 'index' in item
}

const update = async () => {
  if (props.orderType === 'outbound') {
    totalPrice.value = round(item.value.amount * derivedUnitPrice.value)
  } else {
    unitPrice.value = derivedUnitPrice.value
  }

  const payload = {
    product_code: item.value.product.code,
    product_name: item.value.product.name,
    amount: item.value.amount,
    total_price: totalPrice.value,
    unit_price: derivedUnitPrice.value,
    index: index.value,
  }

  const res =
    props.orderType === 'outbound'
      ? await warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder({
          path: { order_code: props.orderCode },
          body: payload,
        })
      : await warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder({
          path: { order_code: props.orderCode },
          body: payload,
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

<style lang="scss" scoped></style>
