<template>
  <div class="flex items-start justify-between gap-4" data-test="toggle-row">
    <div class="flex flex-col">
      <span class="text-sm font-medium">{{ label }}</span>
      <span class="text-xs text-muted">{{ description }}</span>
    </div>
    <q-toggle v-model="modelValue" :aria-label="label" class="shrink-0" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; description: string }>()

const modelValue = defineModel<boolean>({ default: false })
</script>
