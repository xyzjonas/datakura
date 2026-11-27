<template>
  <div class="flex gap-3">
    <q-select
      v-model="type"
      outlined
      clearable
      clear-icon="sym_o_close_small"
      class="w-32"
      label="Typ normy"
      :options="NORM_TYPES"
      data-test="norm-type"
    />
    <q-input
      v-model.trim="code"
      outlined
      class="flex-1"
      label="Norma"
      hint="Hodnota normy, např. 84 (nová norma se založí automaticky)"
      :disable="!type"
      data-test="norm-code"
    />
  </div>
</template>

<script setup lang="ts">
import type { NormRefSchema } from '@/client'

const NORM_TYPES: NormRefSchema['type'][] = ['ISO', 'DIN', 'CSN', 'EN']

const type = defineModel<NormRefSchema['type'] | null | undefined>('type')
const code = defineModel<string | null | undefined>('code')
</script>
