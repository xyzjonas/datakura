<template>
  <MainLayout>
    <RouterView v-slot="{ Component }" :key="$route.path">
      <Suspense>
        <template #default>
          <component :is="Component" />
        </template>
        <template #fallback>
          <span>...loading</span>
        </template>
      </Suspense>
    </RouterView>
  </MainLayout>
</template>

<script setup lang="ts">
import MainLayout from './components/layout/MainLayout.vue'
</script>

<style lang="scss">
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
