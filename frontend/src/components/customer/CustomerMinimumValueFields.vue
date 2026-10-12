<template>
  <div class="grid grid-cols-2 gap-2 items-center">
    <q-checkbox v-model="enabled" label="Zaokrouhlovat na minimální hodnotu položky" />
    <q-input
      v-model.number="minimumItemValue"
      outlined
      type="number"
      min="0"
      clearable
      :disable="!enabled"
      label="Vlastní minimální hodnota"
      hint="Prázdné = použije se globální nastavení"
    />
  </div>
</template>

<script setup lang="ts">
const enabled = defineModel<boolean>('enabled', { default: true })
const minimumItemValue = defineModel<number | null | undefined>('minimumItemValue')
</script>
