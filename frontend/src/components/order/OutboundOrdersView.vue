<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled objednávek</h1>
        <h5 class="text-gray-5 mt-2">Správa příchozích objednávek od zákazníků</h5>
      </div>
      <q-btn
        color="primary"
        unelevated
        label="vytvořit"
        icon="sym_o_add"
        @click="newOrderDialog = true"
      />
    </div>

    <OrdersBaseTable :fetch-orders="fetchOrders" />

    <NewOrderDialog
      v-model="newOrderDialog"
      @create-order="createOrder"
      ref="newOrderDialogComponent"
    ></NewOrderDialog>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersCreateInboundOrder,
  type InboundOrderCreateOrUpdateSchema,
  type InboundOrderSchema,
} from '@/client'
import NewOrderDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { useQuasar } from 'quasar'
import { ref } from 'vue'
import OrdersBaseTable from './OrdersBaseTable.vue'

const { onResponse } = useApi()

// const loading = ref(false)
const fetchOrders = async () => {
  return [] satisfies InboundOrderSchema[] // todo: OUT
}

const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
const $q = useQuasar()
const createOrder = async (params: InboundOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesInboundOrdersCreateInboundOrder({ body: params })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `vydaná objednávka úspěšně vytvořena: ${data.data.code}`,
    })
    router.push({ name: 'incomingOrderDetail', params: { code: data.data.code } })
  }
}
</script>

<style lang="scss" scoped></style>
