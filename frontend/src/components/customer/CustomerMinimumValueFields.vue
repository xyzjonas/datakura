<template>
  <div class="flex flex-col gap-2">
    <div class="flex flex-col">
      <span class="text-sm font-medium">Minimální hodnota položky</span>
      <span class="text-xs text-muted">
        Položky objednávek tohoto zákazníka, jejichž celková cena je nižší než minimální hodnota, se
        zaokrouhlí nahoru na tuto hodnotu. Prázdné pole znamená, že se použije globální minimum z
        nastavení. Zaokrouhlování lze pro zákazníka úplně vypnout přepínačem níže.
      </span>
    </div>
    <q-input
      v-model.number="minimumItemValue"
      outlined
      type="number"
      min="0"
      clearable
      :disable="disable"
      label="Vlastní minimální hodnota"
      hint="Prázdné = použije se globální nastavení"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ disable?: boolean }>()

const minimumItemValue = defineModel<number | null | undefined>('minimumItemValue')
</script>
