<template>
  <div
    :class="[
      flat ? '' : 'shadow-md',
      noPadding ? '' : 'p-4',
      'rounded',
      flat ? '' : 'light:bg-white',
      flat ? '' : 'dark:bg-dark-6',
      flat ? '' : 'border',
      flat ? '' : 'dark:border-dark-3',
      active ? 'active' : '',
      active && flat ? 'active-flat' : '',
      clickable ? 'clickable' : '',
      'relative',
    ]"
  >
    <div v-if="$slots.header" class="bg-muted absolute top-0 left-0 right-0 p-1 px-3 rounded-t">
      <slot name="header"></slot>
    </div>
    <div :class="[$slots.header ? 'pt-[30px]' : '', 'h-full', ...bodyClass]">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    active?: boolean
    clickable?: boolean
    noPadding?: boolean
    flat?: boolean
    bodyClass?: string[]
  }>(),
  {
    active: false,
    clickable: false,
    noPadding: false,
    flat: false,
    bodyClass: () => [],
  },
)
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

.active-flat {
  border: none;
}

.clickable {
  &:hover {
    background-color: #1976d213;
    cursor: pointer;
  }
}
</style>
