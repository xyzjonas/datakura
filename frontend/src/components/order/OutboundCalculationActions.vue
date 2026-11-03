<template>
  <q-btn
    v-if="calculation.state === 'open'"
    unelevated
    color="positive"
    icon="sym_o_order_approve"
    label="vytvořit objednávku"
    :disable="!calculation.items?.length"
    @click="createOrderDialog = true"
  />
  <q-btn
    v-if="editable"
    unelevated
    color="secondary"
    label="Uzavřít"
    icon="sym_o_lock"
    @click="transition('close')"
  />
  <q-btn
    v-else-if="!calculation.order_code"
    unelevated
    color="secondary"
    label="Znovu otevřít"
    icon="sym_o_lock_open"
    @click="transition('reopen')"
  />
  <q-btn
    unelevated
    color="negative"
    label="Smazat"
    icon="sym_o_delete"
    @click="deleteDialog = true"
  />

  <ConfirmDialog
    v-model:show="createOrderDialog"
    title="Vytvořit objednávku?"
    @confirm="createOrder"
  >
    <span>
      Z kalkulace bude vytvořena přijatá objednávka ve stavu
      <OutboundOrderStateBadge state="submitted" />. Kalkulace zůstane beze změny a bude uzavřena.
    </span>
  </ConfirmDialog>

  <ConfirmDialog v-model:show="deleteDialog" title="Smazat kalkulaci?" @confirm="remove">
    <span>Kalkulace zmizí ze seznamů, ale v systému zůstane uložená.</span>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundCalculationsCreateOrderFromOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsDeleteOutboundCalculation,
  warehouseApiRoutesOutboundCalculationsTransitionOutboundCalculation,
  type OutboundCalculationSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { useQuasar } from 'quasar'
import { ref } from 'vue'
import OutboundOrderStateBadge from './OutboundOrderStateBadge.vue'

defineProps<{ editable: boolean }>()

const calculation = defineModel<OutboundCalculationSchema>('calculation', { required: true })
const { onResponse } = useApi()
const { goToOrderOut, goToCalculations } = useAppRouter()
const $q = useQuasar()

const createOrderDialog = ref(false)
const deleteDialog = ref(false)

const createOrder = async () => {
  const response = await warehouseApiRoutesOutboundCalculationsCreateOrderFromOutboundCalculation({
    path: { calculation_code: calculation.value.code },
  })
  const data = onResponse(response)
  if (data) {
    $q.notify({ type: 'positive', message: `Objednávka vytvořena: ${data.data.code}` })
    goToOrderOut(data.data.code)
  }
}

const transition = async (action: 'close' | 'reopen') => {
  const response = await warehouseApiRoutesOutboundCalculationsTransitionOutboundCalculation({
    path: { calculation_code: calculation.value.code },
    body: { action },
  })
  const data = onResponse(response)
  if (data) {
    calculation.value = data.data
  }
}

const remove = async () => {
  const response = await warehouseApiRoutesOutboundCalculationsDeleteOutboundCalculation({
    path: { calculation_code: calculation.value.code },
  })
  if (onResponse(response)) {
    $q.notify({ type: 'positive', message: 'Kalkulace smazána' })
    goToCalculations()
  }
}
</script>
