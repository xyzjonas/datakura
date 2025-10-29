<template>
  <q-input
    dense
    outlined
    rounded
    v-model.trim="modelValue"
    :placeholder="placeholder ?? 'Vyhledat...'"
    :disable="disable"
    :clearable="clearable"
    clear-icon="sym_o_close_small"
    @clear="modelValue = ''"
    :debounce="debounce"
  >
    <template #prepend>
      <q-icon name="search" />
    </template>
  </q-input>
</template>

<script setup lang="ts">
defineProps<{
  placeholder?: string
  disable?: boolean
  clearable?: boolean
  debounce?: number
}>()
const modelValue = defineModel<string>({ required: true })
</script>

<style lang="scss" scoped></style>
