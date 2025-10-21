<template>
  <svg
    :width="width"
    :height="height ?? width"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 16 16"
    fill="none"
  >
    <path
      d="M5 1H4L0 5L4 9H5V6H11C12.6569 6 14 7.34315 14 9C14 10.6569 12.6569 12 11 12H4V14H11C13.7614 14 16 11.7614 16 9C16 6.23858 13.7614 4 11 4H5V1Z"
      fill="#000000"
    />
  </svg>
</template>

<script setup lang="ts">
defineProps<{
  width: string
  height?: string
}>()
</script>

<style lang="scss" scoped></style>
