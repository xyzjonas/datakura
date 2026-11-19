<template>
  <q-btn-dropdown dense flat :label="currency" class="w-20 overflow-hidden">
    <q-list>
      <q-item
        clickable
        v-close-popup
        @click="currency = option"
        v-for="option in currencies"
        :key="option"
      >
        <q-item-section>
          <q-item-label>{{ option }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang="ts">
import { useCurrencySettings } from '@/composables/use-currency-settings'

const currency = defineModel<string>({ required: true })

const { currencies } = useCurrencySettings()
</script>
