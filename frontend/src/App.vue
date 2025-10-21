<template>
  <RouterView v-slot="{ Component }">
    <Suspense>
      <component :is="Component"></component>
      <template #loading>...loading</template>
    </Suspense>
  </RouterView>
</template>

<script setup lang="ts"></script>

<style scoped lang="scss"></style>
