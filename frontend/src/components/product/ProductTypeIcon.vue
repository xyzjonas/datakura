<template>
  <q-icon :name="iconName"></q-icon>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ type: string }>()

const iconName = computed(() => {
  if (props.type.toLowerCase() === 'zboží') {
    return 'sym_o_package_2'
  }
  return 'sym_o_indeterminate_question_box'
})
</script>

<style lang="scss" scoped></style>
