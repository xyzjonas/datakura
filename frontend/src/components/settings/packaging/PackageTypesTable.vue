<template>
  <q-table
    :rows="items"
    :columns="columns"
    loading-label="Načítám"
    flat
    no-data-label="Žádné typy balení nenalezeny"
    class="bg-transparent"
    hide-pagination
    :pagination="{ rowsPerPage: -1 }"
  >
    <template #top-left>
      <q-btn color="primary" unelevated label="vytvořit" icon="add" />
    </template>
    <!-- <template #body-cell-name="props">
      <q-td>
        <a
          @click="
            $router.push({
              name: 'productDetail',
              params: { productCode: props.row.code },
            })
          "
          class="link"
          >{{ props.row.name }}</a
        >
      </q-td>
    </template> -->
    <!-- <template #body-cell-type="props">
      <q-td auto-width>
        <span class="flex items-center gap-1 flex-nowrap">
          <ProductTypeIcon :type="props.row.type" />
          {{ props.row.type }}
        </span>
      </q-td>
    </template> -->
  </q-table>
</template>

<script setup lang="ts">
import { warehouseApiRoutesPackagingGetPackageTypes, type PackageTypeSchema } from '@/client'
import { useApi } from '@/composables/use-api'
import type { QTableColumn } from 'quasar'
import { ref } from 'vue'

const { onResponse } = useApi()

const response = await warehouseApiRoutesPackagingGetPackageTypes()
const data = onResponse(response)

const items = ref<PackageTypeSchema[]>([])
if (data) {
  items.value = data.data
}

const columns: QTableColumn[] = [
  {
    name: 'name',
    field: 'name',
    label: 'Název',
    align: 'left',
  },
  {
    name: 'description',
    field: 'description',
    label: 'Popis',
    align: 'left',
  },
  {
    name: 'amount',
    field: 'amount',
    label: 'Množství',
    align: 'left',
  },
  {
    name: 'unit',
    field: 'unit',
    label: 'MJ',
    align: 'left',
  },
]
</script>

<style lang="scss" scoped></style>
