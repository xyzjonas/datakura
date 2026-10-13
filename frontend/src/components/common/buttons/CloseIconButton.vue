<template>
  <q-btn icon="sym_o_close_small" color="negative" flat dense @click="$emit('click')">
    <slot />
  </q-btn>
</template>

<style lang="scss" scoped></style>
