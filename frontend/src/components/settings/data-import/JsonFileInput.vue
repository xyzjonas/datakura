<template>
  <q-file
    v-model="file"
    outlined
    clearable
    accept=".json,application/json"
    :label="label"
    :hint="hint"
    :disable="disable"
  >
    <template #prepend>
      <q-icon name="sym_o_upload_file" />
    </template>
  </q-file>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  hint?: string
  disable?: boolean
}>()

const file = defineModel<File | null>({ default: null })
</script>
