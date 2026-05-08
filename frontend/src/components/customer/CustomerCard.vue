<template>
  <ForegroundPanel class="flex flex-col min-w-[240px]">
    <template #header>
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-muted">{{ title }}</span>
        <div class="flex items-center gap-1 text-muted">
          <CustomerTypeIcon :type="customer.customer_type" />
          <span>{{ customer.customer_type }}</span>
        </div>
      </div>
    </template>
    <div class="h-full flex flex-col">
      <h2 @click="goToCustomer(customer.code)" class="text-primary link mb-1">
        {{ customer.name }}
      </h2>
      <span class="flex items-center gap-1 text-gray-5 text-sm mb-1">
        <q-icon name="percent" size="16px" />
        <span v-if="customer.discount_group">
          {{ customer.discount_group.name }} ({{ customer.discount_group.discount_percent }} %)
        </span>
        <span v-else>Bez slevové skupiny</span>
      </span>

      <q-badge class="w-fit px-2 py-1 bg-muted light:text-dark dark:text-light">{{
        customer.group.name ?? 'Žádná skupina'
      }}</q-badge>
      <span class="flex items-center gap-1 mt-auto">
        <small class="text-gray-5">kód:</small>
        <h5>{{ customer.code }}</h5>
        <q-btn flat round size="8px" icon="content_copy"></q-btn>
      </span>
    </div>
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
