<template>
  <q-btn flat round size="8px" icon="content_copy" @click="copy(text)"></q-btn>
</template>

<script setup lang="ts">
import { useQuasarClipboard } from '@/composables/use-quasar-clipboard'

defineProps<{
  text: string
}>()
const { copy } = useQuasarClipboard()
</script>
