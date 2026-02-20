<template>
  <div class="flex gap-2">
    <ForegroundPanel
      v-for="item in items"
      :key="item.key"
      class="flex-1"
      @click="activeTabKey = item.key"
      :active="activeTabKey === item.key"
      clickable
    >
      <q-icon v-if="item.icon" :name="item.icon" size="24px"></q-icon>
      <div>
        <h5 class="font-bold uppercase">{{ item.title }}</h5>
      </div>
    </ForegroundPanel>
  </div>
</template>

<script setup lang="ts">
import ForegroundPanel from './ForegroundPanel.vue'

const activeTabKey = defineModel('tab', { required: true })
defineProps<{
  items: {
    title: string
    icon?: string
    key: string
  }[]
}>()
</script>

<style lang="scss" scoped></style>
