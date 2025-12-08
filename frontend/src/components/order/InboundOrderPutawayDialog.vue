<template>
  <ConfirmDialog
    v-model:show="show"
    title="Vytovřit příjemku?"
    @confirm="$emit('confirm', locationCode)"
  >
    <span>
      Nová příjemka bude založena a objednávka přejde do stavu
      <strong class="text-primary">příjem</strong>.

      <q-input
        outlined
        v-model="locationCode"
        label="Skladové místo"
        hint="Skladové místo, kde bude poptávka uložena k naskladnění"
        class="mt-5"
      ></q-input>
    </span>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ConfirmDialog from '../ConfirmDialog.vue'

const show = defineModel<boolean>('show', { default: false })
defineEmits<{
  (e: 'confirm', locationCode: string): void
}>()

const locationCode = ref('AA-00-00')
</script>

<style lang="scss" scoped></style>
