<template>
  <q-stepper
    flat
    v-model="step"
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
      :done="step > 1"
      :header-nav="step > 1"
    >
    </q-step>

    <q-step
      :name="2"
      title="Objednáno"
      caption="čeká na dodání"
      icon="sym_o_delivery_truck_speed"
      active-icon="sym_o_delivery_truck_speed"
      :done="step > 2"
      :header-nav="step > 2"
    >
    </q-step>

    <q-step
      :name="3"
      title="Příjem"
      icon="sym_o_input"
      active-icon="sym_o_input"
      :header-nav="step > 3"
    >
    </q-step>

    <q-step
      :name="4"
      title="Přijato"
      caption="na skladě"
      icon="warehouse"
      active-icon="warehouse"
      :header-nav="step > 3"
    >
    </q-step>
  </q-stepper>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const step = ref(1)
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
