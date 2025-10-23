<template>
  <q-list>
    <q-item
      v-for="item in items"
      :key="item.label"
      clickable
      dense
      v-ripple
      :active="currentRoute.name === item.routeName"
      active-class="dark:bg-pine dark:text-white font-semibold"
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
}

const { currentRoute } = useRouter()

defineProps<{ items: MenuItem[] }>()
</script>

<style lang="scss" scoped></style>
