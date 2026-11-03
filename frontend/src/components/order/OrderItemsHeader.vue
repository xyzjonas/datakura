<template>
  <div class="border rounded shadow-md mb-5">
    <div class="flex items-center justify-between p-4">
      <h2>{{ title }}</h2>
      <q-btn
        unelevated
        color="primary"
        icon="sym_o_add"
        label="přidat položku"
        :disable="disabled"
        @click="emit('add')"
      />
    </div>
    <q-separator />
    <slot />
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{ (e: 'add'): void }>()

defineProps<{ title: string; disabled?: boolean }>()
</script>
