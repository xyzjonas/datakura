<template>
  <q-input dense outlined rounded v-model="modelValue" placeholder="vyhledat...">
    <template #prepend>
      <q-icon name="search" />
    </template>
  </q-input>
</template>

<script setup lang="ts">
const modelValue = defineModel<string>({ required: true })
</script>

<style lang="scss" scoped></style>
