<template>
  <q-btn
    color="primary"
    unelevated
    :label="isCalculation ? 'nová kalkulace' : 'nová objednávka'"
    icon="sym_o_add"
    @click="dialog = true"
  />
  <NewOrderDialog
    v-model:show="dialog"
    :title="isCalculation ? 'Nová kalkulace' : 'Nová objednávka'"
    @create-order="create"
    ref="dialogComponent"
  />
</template>

<script setup lang="ts">
import type { OutboundCalculationCreateOrUpdateSchema } from '@/client'
import NewOrderDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import {
  useOutboundDocumentApi,
  type OutboundDocumentKind,
} from '@/composables/use-outbound-document-api'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'

/** Creates a calculation or a (directly confirmed-by-client) order, depending on `kind`. */
const props = defineProps<{ kind: OutboundDocumentKind }>()

const { onResponse } = useApi()
const { goToOrderOut, goToCalculation } = useAppRouter()
const api = useOutboundDocumentApi(() => props.kind)
const $q = useQuasar()
const isCalculation = computed(() => props.kind === 'calculation')

const dialog = ref(false)
const dialogComponent = ref<InstanceType<typeof NewOrderDialog>>()

const create = async (params: OutboundCalculationCreateOrUpdateSchema) => {
  const data = onResponse(await api.create(params))
  if (data && dialogComponent.value) {
    dialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `${isCalculation.value ? 'kalkulace' : 'objednávka'} úspěšně vytvořena: ${data.data.code}`,
    })
    ;(isCalculation.value ? goToCalculation : goToOrderOut)(data.data.code)
  }
}
</script>
