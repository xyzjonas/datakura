<template>
  <a
    v-if="attachment"
    :href="attachment.url"
    target="_blank"
    rel="noopener"
    class="link inline-flex items-center gap-1 text-sm"
    data-test="certification-file-link"
    @click.stop
  >
    <q-icon name="sym_o_description" size="18px" />
    {{ attachment.name }}
  </a>
  <span v-else class="text-xs text-muted">bez přílohy</span>
</template>

<script setup lang="ts">
import type { MediaFileSchema } from '@/client'

defineProps<{ attachment?: MediaFileSchema | null }>()
</script>
