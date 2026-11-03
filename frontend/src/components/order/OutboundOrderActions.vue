<template>
  <q-btn
    v-if="canConfirm"
    unelevated
    color="positive"
    icon="sym_o_order_approve"
    label="potvrdit"
    @click="confirmDialog = true"
    :disable="!order.items?.length"
  />
  <q-btn
    v-if="editable"
    unelevated
    color="negative"
    label="Uzavřít"
    icon="sym_o_scan_delete"
    @click="cancelDialog = true"
  />

  <ConfirmDialog
    v-model:show="confirmDialog"
    title="Potvrdit přijatou objednávku?"
    @confirm="transition('next')"
  >
    <span>
      Objednávka přejde do stavu <OutboundOrderStateBadge state="picking" /> a bude vytvořena
      výdejka.
    </span>
  </ConfirmDialog>

  <ConfirmDialog
    v-model:show="cancelDialog"
    title="Uzavřít přijatou objednávku?"
    @confirm="transition('cancel')"
  >
    <span>objednávka bude označena jako <OutboundOrderStateBadge state="cancelled" />.</span>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersTransitionOutboundOrder,
  type OutboundOrderSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useApi } from '@/composables/use-api'
import { computed, ref } from 'vue'
import OutboundOrderStateBadge from './OutboundOrderStateBadge.vue'

defineProps<{ editable: boolean }>()

const order = defineModel<OutboundOrderSchema>('order', { required: true })
const { onResponse } = useApi()

// a freshly created order has to be checked and confirmed by hand, only then
// the warehouse order is created
const canConfirm = computed(() => order.value.state === 'submitted')

const confirmDialog = ref(false)
const cancelDialog = ref(false)

const transition = async (action: 'next' | 'cancel') => {
  const response = await warehouseApiRoutesOutboundOrdersTransitionOutboundOrder({
    path: { order_code: order.value.code },
    body: { action },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
  }
}
</script>
