<template>
  <div class="flex items-center gap-3 flex-nowrap">
    <!-- <q-btn dense flat :icon="isOpened ? 'close' : 'menu'" @click="isOpened = !isOpened" /> -->
    <span class="h-[16px] bg-transparent ml-2 flex items-end justify-center rounded gap-1 px-2">
      <span class="h-[8px] w-[6px] bg-red rounded-sm"></span>
      <span class="h-[12px] w-[6px] bg-orange rounded-sm"></span>
      <span class="h-[16px] w-[6px] bg-primary rounded-sm"></span>
    </span>
    <!-- <img src="/logo.svg" class="h-10 bg-light p-1 rounded-full" /> -->
    <q-separator vertical class="my-3 bg-gray h-[1rem]" />
    <a href="/" class="text-dark">
      <span class="font-bold text-xl text-light">SKLAD</span>
    </a>
  </div>
</template>

<script setup lang="ts"></script>

<style lang="scss" scoped></style>
