<template>
  <div class="flex items-start gap-1">
    <div class="flex flex-col">
      <q-btn
        flat
        dense
        round
        size="xs"
        icon="sym_o_keyboard_arrow_up"
        :disable="index === 0"
        data-test="move-up"
        @click="emit('move', -1)"
      />
      <q-btn
        flat
        dense
        round
        size="xs"
        icon="sym_o_keyboard_arrow_down"
        :disable="index === count - 1"
        data-test="move-down"
        @click="emit('move', 1)"
      />
    </div>
    <div class="min-w-0 flex-1">
      <slot />
    </div>
    <q-btn
      flat
      dense
      round
      size="sm"
      icon="sym_o_close"
      data-test="remove"
      @click="emit('remove')"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ index: number; count: number }>()
const emit = defineEmits<{ move: [by: -1 | 1]; remove: [] }>()
</script>
