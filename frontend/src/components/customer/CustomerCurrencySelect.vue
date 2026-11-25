<template>
  <q-select
    v-model="currency"
    :options="currencies"
    outlined
    clearable
    emit-value
    map-options
    label="Měna zákazníka"
    :hint="`Prázdné = základní měna (${baseCurrency}). Objednávky zákazníka se vystavují a fakturují v této měně.`"
    data-test="customer-currency"
  />
</template>

<script setup lang="ts">
import { useCurrencySettings } from '@/composables/use-currency-settings'

const currency = defineModel<string | null>({ default: null })

const { currencies, baseCurrency } = useCurrencySettings()
</script>
