<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled vydaných dobropisů</h1>
        <h5 class="text-gray-5 mt-2">Správa ...</h5>
      </div>
    </div>
    <CreditNotesBaseTable
      :fetch-credit-notes="fetchCreditNotes"
      entityRouteName="creditNoteToSupplier"
    />
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesCreditNotesGetCreditNotesToSupplier } from '@/client'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import { type Ref } from 'vue'
import CreditNotesBaseTable, { type Pagination } from './CreditNotesBaseTable.vue'

const { onResponse } = useApi()
const { page, pageSize, search } = useQueryProducts()

const fetchCreditNotes = async (pagination: Ref<Pagination>, loading: Ref<boolean>) => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesCreditNotesGetCreditNotesToSupplier({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    const data = onResponse(res)
    if (data) {
      pagination.value.rowsNumber = data.count
      return data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }

  return []
}
</script>

<style lang="scss" scoped></style>
