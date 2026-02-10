<template>
  <div class="flex flex-col">
    <span class="text-gray-5 text-2xs">DOBROPIS</span>
    <div class="flex items-center gap-2">
      <a class="link text-lg" @click="goToCreditNote(note.code)">{{ note.code }} </a>
      <GenericStateBadge :state="note.state" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CreditNoteBaseSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import GenericStateBadge from '../GenericStateBadge.vue'

const { goToCreditNote } = useAppRouter()

defineProps<{ note: CreditNoteBaseSchema }>()
</script>

<style lang="scss" scoped></style>
