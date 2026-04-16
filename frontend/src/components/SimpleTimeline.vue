<template>
  <div class="flex flex-row w-full justify-center gap-3 flex-nowrap">
    <div
      v-for="(item, index) in items"
      :key="item.key"
      class="flex gap-3 flex-nowrap justify-around"
    >
      <span v-if="index > 0 && $q.screen.gt.sm" class="self-center">
        <q-icon name="sym_o_keyboard_double_arrow_right" />
      </span>
      <div
        :class="[
          getItemClass(item, index),
          'flex items-center gap-2 flex-nowrap timeline-item md:border p-2 rounded-xl px-3',
          ,
          $q.screen.gt.sm ? '' : '',
        ]"
      >
        <span
          :class="[
            'bg-gray-5',
            item.key === props.activeKey ? 'bg-primary' : '',
            index < activeIndex ? 'bg-positive' : '',
            'w-4 sm:w-6 h-4 sm:h-6 rounded-full flex items-center justify-center',
          ]"
        >
          <q-icon
            v-if="$q.screen.gt.sm"
            :name="index < activeIndex ? 'sym_o_check' : item.icon"
            color="white"
          />
        </span>
        <div :class="[$q.screen.lt.md && index !== activeIndex ? 'hidden' : '', 'flex flex-col']">
          <span class="font-600">{{ item.title }}</span>
          <span v-if="$q.screen.gt.md" class="font-500 text-2xs">{{ item.caption }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type TimelineItem = {
  title: string
  caption?: string
  key: string
  icon: string
}
const props = defineProps<{
  items: TimelineItem[]
  activeKey: string
}>()

const activeIndex = computed(() => props.items.findIndex((item) => item.key === props.activeKey))

const getItemClass = (item: TimelineItem, index: number) => {
  let clazz = ''
  if (index > activeIndex.value) {
    clazz = clazz + 'text-gray-5 '
  } else if (index === activeIndex.value) {
    clazz = clazz + 'text-primary border-primary '
  } else {
    clazz = clazz + 'text-positive border-positive '
  }
  return clazz
}
</script>

<style lang="scss" scoped></style>
