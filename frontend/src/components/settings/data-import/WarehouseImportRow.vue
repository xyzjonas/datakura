<template>
  <div class="flex items-start gap-3">
    <q-input
      v-model.trim="row.warehouse"
      outlined
      label="Sklad"
      hint="Název cílového skladu (vytvoří se, pokud neexistuje)"
      maxlength="50"
      :disable="disable"
      class="flex-1"
    />
    <JsonFileInput
      v-model="row.file"
      label="Soubor se skladovými místy"
      hint="JSON se seznamem lokací a položek"
      :disable="disable"
      class="flex-[2]"
    />
    <q-btn
      flat
      round
      dense
      icon="delete"
      color="negative"
      class="mt-3"
      :disable="disable"
      @click="emit('remove')"
    >
      <q-tooltip>Odebrat řádek</q-tooltip>
    </q-btn>
  </div>
</template>

<script setup lang="ts">
import JsonFileInput from './JsonFileInput.vue'
import type { WarehouseImportRowModel } from './data-import-body'

defineProps<{ disable?: boolean }>()
const emit = defineEmits<{ remove: [] }>()

const row = defineModel<WarehouseImportRowModel>({ required: true })
</script>
