<template>
  <ForegroundPanel
    no-padding
    @click="onClick"
    :class="['panel', to ? 'hover:cursor-pointer' : '', 'relative']"
  >
    <div class="p-5">
      <h2>{{ title }}</h2>
      <h5 class="text-gray-5">{{ subtitle }}</h5>
    </div>
    <span v-if="to" class="absolute top-2 right-3 icon-wrapper">
      <q-icon name="sym_o_left_click" color="gray" class="icon"></q-icon>
    </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '../ForegroundPanel.vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  title: string
  subtitle?: string
  to?: RouteLocationRaw
}>()

const router = useRouter()
const onClick = () => {
  if (props.to) {
    router.push(props.to)
  }
}
</script>

<style lang="scss" scoped>
.icon {
  transition: color 0.3s ease;
}

.panel:hover .icon {
  color: #207ed8 !important;
}
</style>
