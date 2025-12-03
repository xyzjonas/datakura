<template>
  <q-stepper
    flat
    :model-value="step"
    header-nav
    ref="stepper"
    color="primary"
    animated
    class="shadow-none bg-transparent"
    inactive-color="gray-5"
    done-color="positive"
  >
    <q-step
      :name="1"
      title="Rozpracováno"
      caption="čeká na potvrzení"
      icon="sym_o_ink_pen"
      active-icon="sym_o_ink_pen"
      active-color="accent"
      :done="step > 1"
      :header-nav="step > 1"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>

    <q-step
      :name="2"
      title="Potvrzeno"
      caption="čeká na dodání"
      icon="sym_o_delivery_truck_speed"
      active-icon="sym_o_delivery_truck_speed"
      active-color="accent"
      :done="step > 2"
      :header-nav="step > 2"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>

    <q-step
      :name="3"
      title="Příjem"
      caption="zboží je na příjmu"
      icon="sym_o_input"
      active-icon="sym_o_input"
      active-color="accent"
      :done="step > 3"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>

    <q-step
      :name="50"
      title="Přijato"
      caption="naskladněno"
      icon="warehouse"
      active-icon="warehouse"
      active-color="accent"
      :done="step >= 4"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>
  </q-stepper>
</template>

<script setup lang="ts">
import { CANCELLED, INBOUND_ORDER_STATES } from '@/constants/inbound-order'
import { computed } from 'vue'

const props = defineProps<{ state: string }>()
const step = computed(() => INBOUND_ORDER_STATES[props.state]?.step ?? CANCELLED)
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
