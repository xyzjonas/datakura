<template>
  <div class="flex-1">
    <div class="mb-2 flex items-center justify-between">
      <div>
        <h1>Přehled vydaných faktur</h1>
        <h5 class="mt-2 text-gray-5">Systémově generované faktury pro odběratele</h5>
      </div>
    </div>

    <InvoicesBaseTable :fetch-invoices="fetchInvoices" direction="outbound" />
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesInvoicesGetOutboundInvoices, type InvoiceSchema } from '@/client'
import { useApi } from '@/composables/use-api'
import { useInvoicesQuery } from '@/composables/query/use-invoices-query'
import type { Ref } from 'vue'
import InvoicesBaseTable, { type Pagination } from './InvoicesBaseTable.vue'

const { onResponse } = useApi()
const { page, pageSize } = useInvoicesQuery()

const fetchInvoices = async (pagination: Ref<Pagination>, loading: Ref<boolean>) => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesInvoicesGetOutboundInvoices({
      query: {
        page: page.value,
        page_size: pageSize.value,
      },
    })
    const data = onResponse(response)
    if (data) {
      pagination.value.rowsNumber = data.count
      return data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }

  return [] as InvoiceSchema[]
}
</script>
