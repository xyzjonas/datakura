<template>
  <div class="px-2 pb-2">
    <q-card
      flat
      class="rounded border border-white/10 bg-white/6 text-white shadow-none flex flex-col p-3"
    >
      <div class="flex gap-3 items-center">
        <div
          class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-3 bg-primary/15 text-primary"
        >
          <q-icon name="sym_o_badge" size="22px" />
        </div>
        <div class="flex flex-col">
          <div class="text-2xs font-medium uppercase tracking-[0.12em] text-gray-4">
            Vlastní firma
          </div>
          <div v-if="selfCustomer" class="mt-1 truncate text-base font-semibold text-white">
            {{ selfCustomer.name }}
          </div>
          <div v-else class="mt-1 truncate text-base font-semibold text-white">Nenastaveno</div>
        </div>
      </div>
      <q-tooltip class="w-sm text-3">
        <span v-if="selfCustomer">
          Tato firma je nastavená jako vlastní a systém ji použije v interních dokladech.
        </span>

        <span v-else>
          Vlastní firma zatím není nastavená. V seznamu zákazníků označte jednu firmu jako vlastní,
          aby ji šlo použít v příjemkách, fakturách a dalších dokladech.
        </span>
      </q-tooltip>
    </q-card>
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesCustomerGetCustomers, type CustomerSchema } from '@/client'
import { useApi } from '@/composables/use-api'
import { onMounted, ref } from 'vue'

const selfCustomer = ref<CustomerSchema>()
const isLoading = ref(true)
const { onResponse } = useApi()

const loadSelfCustomer = async () => {
  isLoading.value = true
  try {
    const response = await warehouseApiRoutesCustomerGetCustomers({
      query: {
        is_self: true,
        page: 1,
        page_size: 1,
      },
    })
    const data = onResponse(response)
    selfCustomer.value = data?.data[0]
  } catch {
    selfCustomer.value = undefined
  } finally {
    isLoading.value = false
  }
}

onMounted(loadSelfCustomer)
</script>
