<template>
  <ForegroundPanel class="flex flex-col">
    <div class="text-gray-5 flex items-center justify-between gap-1 mb-1">
      <span>{{ title }}</span>
      <div class="flex items-center gap-1">
        <CustomerTypeIcon :type="customer.customer_type" />
        <span>{{ customer.customer_type }}</span>
      </div>
    </div>
    <h1 @click="goToCustomer(customer.code)" class="text-primary link mb-2">
      {{ customer.name }}
    </h1>
    <span class="flex items-center gap-1 mt-3">
      <small class="text-gray-5">kód:</small>
      <h5>{{ customer.code }}</h5>
      <q-btn flat round size="8px" icon="content_copy"></q-btn>
    </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { CustomerSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import ForegroundPanel from '../ForegroundPanel.vue'
import CustomerTypeIcon from './CustomerTypeIcon.vue'

defineProps<{ customer: CustomerSchema; title: string }>()

const { goToCustomer } = useAppRouter()
</script>

<style lang="scss" scoped></style>
