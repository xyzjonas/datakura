<template>
  <div
    :class="[
      'shadow-md',
      noPadding ? '' : 'p-5',
      'rounded',
      'light:bg-white',
      'dark:bg-dark-6',
      'border',
      'dark:border-dark-3',
      active ? 'active' : '',
      clickable ? 'clickable' : '',
    ]"
  >
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ active?: boolean; clickable?: boolean; noPadding?: boolean }>()
</script>

<style lang="scss" scoped>
div {
  transition: all 0.2s ease-in-out;
  // border: 1px solid rgb(66 66 66 / var(--un-border-opacity));
}

.active {
  border: 1px solid #1976d24b;
  color: $primary;
}

.clickable {
  &:hover {
    background-color: #1976d213;
    cursor: pointer;
  }
}
</style>
