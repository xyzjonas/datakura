<template>
  <ForegroundPanel
    no-padding
    @click="onClick"
    :class="['panel', to ? 'hover:cursor-pointer' : '', 'relative']"
  >
    <div :class="[caption ? 'p-5 pt-4' : 'p-5']">
      <small v-if="caption" class="text-gray-5">{{ caption }}</small>
      <h2>{{ title }}</h2>
      <h5 class="text-gray-5">{{ subtitle }}</h5>
    </div>
    <div>
      <AreaChart
        :data="data"
        :categories="categories"
        :height="64"
        :width="'100%'"
        xLabel="Month"
        yLabel="Amount"
        hide-legend
        hide-x-axis
        hide-y-axis
      />
    </div>
    <span v-if="to" class="absolute top-2 right-3 icon-wrapper">
      <q-icon name="sym_o_left_click" color="gray" class="icon"></q-icon>
    </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { AreaChart } from 'vue-chrts'
import ForegroundPanel from '../ForegroundPanel.vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import { computed } from 'vue'

interface SeriesConfig {
  key: string
  label: string
  color: string
}

const props = defineProps<{
  title: string
  caption?: string
  subtitle?: string
  data: Partial<Record<string, unknown>>[]
  // Single-series mode (deprecated, use series instead)
  dataKey?: string
  dataLabel?: string
  color?: string
  // Multi-series mode
  series?: SeriesConfig[]
  xAxisKey: string
  to?: RouteLocationRaw
}>()

const categories = computed(() => {
  if (props.series && props.series.length > 0) {
    return Object.fromEntries(
      props.series.map((s) => [
        s.key,
        {
          name: s.label,
          color: s.color,
        },
      ]),
    )
  }

  // Fallback to single-series mode
  if (props.dataKey && props.dataLabel && props.color) {
    return {
      [props.dataKey]: {
        name: props.dataLabel,
        color: props.color,
      },
    }
  }

  return {}
})

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
