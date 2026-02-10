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
      :name="1"
      title="Kontrola"
      caption="Probíhá validace objednávky"
      icon="sym_o_search"
      active-icon="sym_o_search"
      active-color="accent"
      :done="step > 1"
      :header-nav="step > 1"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>

    <q-step
      :name="2"
      title="Připraveno"
      caption="Zboží čeká na příjmu"
      icon="sym_o_pallet"
      active-icon="sym_o_pallet"
      active-color="accent"
      :done="step > 2"
      :header-nav="step > 2"
      :error="step >= CANCELLED"
      error-color="negative"
    >
    </q-step>

    <q-step
      :name="3"
      title="Příjem zahájen"
      caption="Probíhá příjem"
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
      caption="Naskladněno"
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
import type { InboundWarehouseOrderSchema } from '@/client'
import { CANCELLED, getInboundWarehouseOrderStep } from '@/constants/inbound-warehouse-order'
import { computed } from 'vue'

const props = defineProps<{ order: InboundWarehouseOrderSchema }>()
const step = computed(() => getInboundWarehouseOrderStep(props.order))
</script>

<style lang="scss" scoped>
:deep(.q-stepper__content) {
  display: none;
}
</style>
