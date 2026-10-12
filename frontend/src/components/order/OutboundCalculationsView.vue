<template>
  <div class="flex-1">
    <div class="mb-2 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="min-w-0">
        <h1>Kalkulace přijatých objednávek</h1>
        <h5 class="mt-2 text-gray-5">
          Rozpracované kalkulace pro zákazníky, které se po potvrzení změní na přijaté objednávky
        </h5>
      </div>
      <OutboundCalculationCreateButton />
    </div>

    <OutboundOrdersTable v-model:customer-filter="customerFilter" calculations />
  </div>
</template>

<script setup lang="ts">
import type { CustomerSchema } from '@/client'
import OutboundCalculationCreateButton from '@/components/order/OutboundCalculationCreateButton.vue'
import OutboundOrdersTable from '@/components/order/OutboundOrdersTable.vue'
import { ref } from 'vue'

const customerFilter = ref<CustomerSchema>()
</script>
