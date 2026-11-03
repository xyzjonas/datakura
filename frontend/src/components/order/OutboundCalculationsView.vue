<template>
  <div class="flex-1">
    <div class="mb-2 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="min-w-0">
        <h1>Přehled rozpracovaných nabídek</h1>
        <h5 class="mt-2 text-gray-5">
          Nabídky pro zákazníky. Po potvrzení kupujícím se z nabídky vytvoří přijatá objednávka.
        </h5>
      </div>
      <OutboundDocumentCreateButton kind="calculation" />
    </div>

    <OutboundOrdersTable v-model:customer-filter="customerFilter" calculations />
  </div>
</template>

<script setup lang="ts">
import type { CustomerSchema } from '@/client'
import OutboundDocumentCreateButton from '@/components/order/OutboundDocumentCreateButton.vue'
import OutboundOrdersTable from '@/components/order/OutboundOrdersTable.vue'
import { ref } from 'vue'

const customerFilter = ref<CustomerSchema>()
</script>
