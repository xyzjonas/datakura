<template>
  <ForegroundPanel class="flex flex-col flex-1">
    <div class="mb-2">
      <h2>{{ calculations ? 'Kalkulace' : 'Historie objednávek' }}</h2>
      <span class="text-gray-5">
        {{
          calculations
            ? 'Všechny kalkulace pro tohoto zákazníka ve všech stavech'
            : 'Všechny přijaté objednávky od tohoto zákazníka ve všech stavech'
        }}
      </span>
    </div>
    <SimpleOutboundOrdersTable
      :customer-code="customerCode"
      :calculations="calculations"
      include-all
      class="flex-1"
    />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import SimpleOutboundOrdersTable from '@/components/order/SimpleOutboundOrdersTable.vue'

defineProps<{
  customerCode: string
  calculations?: boolean
}>()
</script>
