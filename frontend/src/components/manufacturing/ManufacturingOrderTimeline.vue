<template>
  <q-stepper
    flat
    :model-value="step"
    color="primary"
    animated
    class="shadow-none bg-transparent"
    inactive-color="gray-5"
    done-color="positive"
  >
    <q-step
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
    />

    <q-step
      :name="2"
      title="Potvrzeno"
      caption="Zboží čeká na výdej na pracoviště"
      icon="sym_o_order_approve"
      active-icon="sym_o_order_approve"
      active-color="accent"
      :done="step > 2"
      :header-nav="step > 2"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    />

    <q-step
      :name="3"
      title="Zpracovává se"
      caption="Zboží je na pracovišti"
      icon="sym_o_manufacturing"
      active-icon="sym_o_manufacturing"
      active-color="accent"
      :done="step > 3"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    />

    <q-step
      :name="4"
      title="Dokončeno"
      caption="Výroba dokončena"
      icon="sym_o_check_circle"
      active-icon="sym_o_check_circle"
      active-color="accent"
      :done="step >= 4"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    />
  </q-stepper>
</template>

<script setup lang="ts">
import { CANCELLED, MANUFACTURING_ORDER_STATES } from '@/constants/manufacturing-order'
import { computed } from 'vue'

const props = defineProps<{ state: string }>()
const step = computed(() => MANUFACTURING_ORDER_STATES[props.state]?.step ?? CANCELLED)
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
