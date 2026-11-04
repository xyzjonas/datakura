<template>
  <div class="flex min-w-0 flex-col justify-between gap-2 px-4 py-3">
    <div class="flex items-center justify-between gap-2">
      <div class="text-xs uppercase tracking-wide text-muted">{{ label }}</div>
      <slot name="action" />
    </div>
    <div>
      <slot />
    </div>
    <div v-if="caption" class="text-xs text-gray-5">{{ caption }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; caption?: string }>()
</script>
