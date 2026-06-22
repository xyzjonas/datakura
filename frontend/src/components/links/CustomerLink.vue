<template>
  <router-link
    class="link w-30 truncate block"
    :to="{ name: 'customerDetail', params: { customerCode: customer.code } }"
  >
    {{ customer.name }}
  </router-link>
</template>

<script setup lang="ts">
import type { CustomerSchema } from '@/client'

defineProps<{ customer: Pick<CustomerSchema, 'code' | 'name'> }>()
</script>

<style lang="scss" scoped></style>
