<template>
  <q-btn
    color="primary"
    unelevated
    label="nová kalkulace"
    icon="sym_o_add"
    @click="dialog = true"
  />
  <NewOrderDialog v-model="dialog" @create-order="createCalculation" ref="dialogComponent" />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersCreateOutboundOrder,
  type OutboundOrderCreateOrUpdateSchema,
} from '@/client'
import NewOrderDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const { onResponse } = useApi()
const { goToOrderOut } = useAppRouter()
const $q = useQuasar()

const dialog = ref(false)
const dialogComponent = ref<InstanceType<typeof NewOrderDialog>>()

const createCalculation = async (params: OutboundOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesOutboundOrdersCreateOutboundOrder({ body: params })
  const data = onResponse(response)
  if (data && dialogComponent.value) {
    dialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `kalkulace úspěšně vytvořena: ${data.data.code}`,
    })
    goToOrderOut(data.data.code)
  }
}
</script>
