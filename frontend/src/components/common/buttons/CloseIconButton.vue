<template>
  <q-btn icon="sym_o_close_small" color="negative" flat dense @click="$emit('click')">
    <slot />
  </q-btn>
</template>

<style lang="scss" scoped></style>

<script setup lang="ts">
// declared so the click is not also forwarded natively to the root (double firing)
defineEmits<{ (e: 'click'): void }>()
</script>
