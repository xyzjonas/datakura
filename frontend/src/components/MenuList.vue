<template>
  <q-list class="pl-3">
    <q-item
      v-for="item in items"
      :key="item.label"
      clickable
      dense
      v-ripple
      :active="isActive(item)"
      active-class="light:bg-primary dark:bg-light-9 light:text-white dark:text-dark"
      :to="{ name: item.routeName }"
      class="rounded-md my-2"
    >
      <q-item-section avatar>
        <q-icon :name="item.icon" />
      </q-item-section>
      <q-item-section> {{ item.label }} </q-item-section>
    </q-item>
  </q-list>
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

defineProps<{ items: MenuItem[] }>()

const isActive = (item: MenuItem) => {
  if (item.routeMatch) {
    return item.routeMatch.includes(String(currentRoute.value.name))
  }
  return item.routeName.includes(String(currentRoute.value.name))
}
</script>

<style lang="scss" scoped></style>
