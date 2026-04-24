<template>
  <q-stepper
    flat
    :model-value="step"
    ref="stepper"
    color="primary"
    animated
    class="shadow-none bg-transparent"
    inactive-color="gray-5"
    done-color="positive"
  >
    <q-step
      v-if="step < 2"
      :name="1"
      title="Koncept"
      caption="Čeká na potvrzení"
      icon="sym_o_ink_pen"
      active-icon="sym_o_ink_pen"
      active-color="accent"
      :done="step > 1"
      :header-nav="step > 1"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      :name="2"
      title="Potvrzeno"
      caption="Objednávka potvrzena"
      icon="sym_o_approval_delegation"
      active-icon="sym_o_approval_delegation"
      active-color="accent"
      :done="step > 2"
      :header-nav="step > 2"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      :name="3"
      title="Kompletace"
      caption="Zboží se kompletuje"
      icon="sym_o_handyman"
      active-icon="sym_o_handyman"
      active-color="accent"
      :done="step > 3"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      :name="4"
      title="Odesláno"
      caption="Výdejka dokončena"
      icon="sym_o_send"
      active-icon="sym_o_send"
      active-color="accent"
      :done="step > 4"
      :header-nav="step > 4"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      v-if="step > 3"
      :name="5"
      title="Vyfakturováno"
      caption="Faktura vystavena"
      icon="sym_o_receipt_long"
      active-icon="sym_o_receipt_long"
      active-color="accent"
      :done="step > 5"
      :header-nav="step > 5"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      v-if="step > 5"
      :name="6"
      title="Čeká na úhradu"
      caption="Po splatnosti bez úhrady"
      icon="sym_o_hourglass_top"
      active-icon="sym_o_hourglass_top"
      active-color="warning"
      :done="step > 6"
      :header-nav="step > 6"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      :name="7"
      title="Dokončeno / uhrazeno"
      caption="Objednávka uzavřena"
      icon="sym_o_check_circle"
      active-icon="sym_o_check_circle"
      active-color="positive"
      :done="step >= 7"
      :header-nav="step > 6"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>
  </q-stepper>
</template>

<script setup lang="ts">
import { CANCELLED, OUTBOUND_ORDER_STATES } from '@/constants/outbound-order'
import { computed } from 'vue'

const props = defineProps<{ state: string }>()
const step = computed(() => OUTBOUND_ORDER_STATES[props.state]?.step ?? CANCELLED)
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
