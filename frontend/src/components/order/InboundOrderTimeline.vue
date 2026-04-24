<template>
  <!-- <simple-timeline :items="items" :activeKey="state" /> -->
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
      title="Objednáno"
      caption="Zboží je na cestě"
      icon="sym_o_delivery_truck_speed"
      active-icon="sym_o_delivery_truck_speed"
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
      title="Příjem"
      caption="Zboží čeká na příjem"
      icon="sym_o_fact_check"
      active-icon="sym_o_fact_check"
      active-color="accent"
      :done="step > 3"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      v-if="step > 1"
      :name="4"
      title="Naskladnění"
      caption="Zboží je připraveno k naskladění"
      icon="sym_o_input"
      active-icon="sym_o_input"
      active-color="accent"
      :done="step > 3"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>

    <q-step
      :name="50"
      title="Přijato"
      caption="Naskladněno"
      icon="warehouse"
      active-icon="warehouse"
      active-color="accent"
      :done="step >= 5"
      :header-nav="step > 3"
      :error="step >= CANCELLED"
      error-color="negative"
      error-icon="block"
    >
    </q-step>
  </q-stepper>
</template>

<script setup lang="ts">
import { CANCELLED, INBOUND_ORDER_STATES } from '@/constants/inbound-order'
import { computed } from 'vue'
// import SimpleTimeline from '../SimpleTimeline.vue'

const props = defineProps<{ state: string }>()
const step = computed(() => INBOUND_ORDER_STATES[props.state]?.step ?? CANCELLED)

// const items = Object.entries(INBOUND_ORDER_STATES).map(([key, value]) => ({
//   title: value.label,
//   caption: value.caption,
//   icon: value.icon,
//   key,
// }))
// const items = [
//   {
//     title: 'Koncept',
//     caption: 'Čeká na potvrzení',
//     icon: 'sym_o_ink_pen',
//   },
//   {
//     title: 'Objednáno',
//     caption: 'Zboží je na cestě',
//     icon: 'sym_o_delivery_truck_speed',
//   },
//   {
//     title: 'Příjem',
//     caption: 'Zboží čeká na příjem',
//     icon: 'sym_o_fact_check',
//   },
//   {
//     title: 'Naskladnění',
//     caption: 'Zboží je připraveno k naskladnění',
//     icon: 'sym_o_input',
//   },
//   {
//     title: 'Přijato',
//     caption: 'Naskladněno',
//     icon: 'warehouse',
//   },
// ]
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
