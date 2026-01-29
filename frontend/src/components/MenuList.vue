<template>
  <q-item
    v-for="item in items"
    :key="item.label"
    clickable
    v-ripple
    :active="isActive(item)"
    active-class="light:bg-primary_light dark:bg-primary light:text-white dark:text-white"
    :to="{ name: item.routeName }"
    :class="{ 'rounded-md': true }"
    dense
    dark
  >
    <q-item-section avatar>
      <q-icon :name="item.icon" />
    </q-item-section>
    <q-item-section> {{ item.label }} </q-item-section>
  </q-item>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

type MenuItem = {
  label: string
  icon: string
  routeName: string
  routeMatch?: string
}

const { currentRoute } = useRouter()

defineProps<{ items: MenuItem[]; inset?: boolean }>()

const isActive = (item: MenuItem) => {
  if (item.routeMatch) {
    return item.routeMatch.includes(String(currentRoute.value.name))
  }
  return item.routeName.includes(String(currentRoute.value.name))
}
</script>
<style lang="css" scoped>
a {
  color: white !important;
}
</style>
