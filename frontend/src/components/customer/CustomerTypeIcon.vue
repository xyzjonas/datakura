<template>
  <q-icon :name="iconName"></q-icon>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ type: string }>()

const iconName = computed(() => {
  if (props.type.toLowerCase().includes('firm')) {
    return 'sym_o_domain'
  }
  if (props.type.toLowerCase() === 'osoba') {
    return 'sym_o_person'
  }
  return 'sym_o_indeterminate_question_box'
})
</script>

<style lang="scss" scoped></style>
