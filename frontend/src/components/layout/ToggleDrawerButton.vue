<template>
  <q-btn dense flat :icon="isOpened ? 'close' : 'menu'" @click="toggle" />
</template>

<script setup lang="ts">
import { useDrawer } from '@/composables/use-drawer'

const { isOpened, toggle } = useDrawer()
</script>

<style lang="scss" scoped></style>
