<template>
  <a
    v-if="attachment"
    :href="attachment.url"
    target="_blank"
    rel="noopener"
    class="link inline-flex items-center gap-1 text-sm max-w-full"
    data-test="certification-file-link"
    :aria-label="attachment.name"
    @click.stop
  >
    <q-icon name="sym_o_description" size="18px" class="shrink-0" />
    <span v-if="!compact" class="truncate">{{ attachment.name }}</span>
    <q-tooltip v-if="compact">{{ attachment.name }}</q-tooltip>
  </a>
  <span v-else class="text-xs text-muted">bez přílohy</span>
</template>

<script setup lang="ts">
import type { MediaFileSchema } from '@/client'

defineProps<{
  attachment?: MediaFileSchema | null
  /** Icon only (file name in a tooltip) - for narrow places like tables in dialogs. */
  compact?: boolean
}>()
</script>
