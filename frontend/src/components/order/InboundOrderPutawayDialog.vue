<template>
  <ConfirmDialog
    v-model:show="show"
    title="Potvrdit přechod do příjmu?"
    @confirm="$emit('confirm')"
  >
    <span>
      Objednávka přejde do stavu <InboundOrderStateBadge state="receiving" /> a následně bude
      založena příjemka.
    </span>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import ConfirmDialog from '../ConfirmDialog.vue'
import InboundOrderStateBadge from './InboundOrderStateBadge.vue'

const show = defineModel<boolean>('show', { default: false })

defineEmits<{
  (e: 'confirm'): void
}>()
</script>

<style lang="scss" scoped></style>
