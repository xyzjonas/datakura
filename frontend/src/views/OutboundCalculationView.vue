<template>
  <OutboundDocumentView :code="code" kind="calculation" />
</template>

<script setup lang="ts">
import OutboundDocumentView from '@/components/order/OutboundDocumentView.vue'

defineProps<{ code: string }>()
</script>
