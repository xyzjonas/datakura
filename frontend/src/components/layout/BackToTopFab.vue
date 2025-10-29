<template>
  <q-page-sticky position="bottom-right" :offset="[8, 8]" class="z-8">
    <transition name="fade">
      <q-btn
        v-if="scrolledPerc > 1"
        dense
        padding="8px"
        icon="arrow_upward"
        color="primary"
        @click="y = 0"
      />
    </transition>
  </q-page-sticky>
</template>
<script setup lang="ts">
import { useWindowSize, useWindowScroll } from '@vueuse/core'
import { computed } from 'vue'

const { height } = useWindowSize()
const { y } = useWindowScroll({ behavior: 'smooth' })
const scrolledPerc = computed(() => y.value / height.value)
</script>

<style lang="scss" scoped></style>
