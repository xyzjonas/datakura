<template>
  <q-input
    v-model.trim="code"
    outlined
    :dense="dense"
    label="Kód zákazníka"
    :hint="missing ? undefined : 'Kód produktu používaný zákazníkem'"
    :error="missing"
    error-message="Zákazník vyžaduje vlastní kód - bez něj nelze objednávku potvrdit"
    :debounce="debounce"
    maxlength="100"
    data-test="customer-product-code-input"
  >
    <template #prepend>
      <q-icon name="sym_o_tag" />
    </template>
  </q-input>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** Customer needs the code - an empty field is highlighted red. */
  required?: boolean
  dense?: boolean
  debounce?: number
}>()

const code = defineModel<string | null | undefined>({ default: null })

const missing = computed(() => !!props.required && !code.value)
</script>
