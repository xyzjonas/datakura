<template>
  <div
    class="shrink-0 rounded-full overflow-hidden flex items-center justify-center select-none bg-primary text-light font-bold uppercase"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * 0.45}px` }"
  >
    <img v-if="url" :src="url" alt="" class="w-full h-full object-cover" />
    <span v-else data-test="avatar-initial">{{ initial }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    username?: string
    url?: string | null
    size?: number
  }>(),
  { username: '', url: null, size: 36 },
)

const initial = computed(() => props.username.trim().charAt(0))
</script>
