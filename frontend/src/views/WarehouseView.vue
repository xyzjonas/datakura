<template>
  <MainLayout>
    <ForegroundPanel class="pr-10 min-w-[256px]">
      <q-tree
        :nodes="simple"
        node-key="label"
        selected-color="primary"
        v-model:selected="location"
        default-expand-all
      >
        <template v-slot:default-header="prop">
          <div class="flex items-center">
            <q-icon :name="prop.node.icon" class="mr-2" color="gray-5" size="18px" />
            <span :class="{ 'font-bold': location === prop.node.label }">{{
              prop.node.label
            }}</span>
          </div>
        </template>
      </q-tree>
    </ForegroundPanel>

    <ForegroundPanel class="flex-[5]" v-if="warehouseLocation">
      <div class="flex justify-between items-center">
        <h1 class="mb-5">{{ warehouseLocation.code }}</h1>
        <q-toggle v-model="aggregate">
          <span class="text-gray"> Sloučit podle typu balení </span>
        </q-toggle>
      </div>

      <q-table
        :rows="rows"
        :columns="columns"
        flat
        :pagination="{ rowsPerPage: -1 }"
        hide-pagination
      >
        <template #body-cell-name="props">
          <q-td>
            <span class="link">{{ props.row.stock_item.name }}</span>
          </q-td>
        </template>
        <template #body-cell-totalCount="props" v-if="aggregate">
          <q-td auto-width> {{ props.row.itemsCount }} ks </q-td>
        </template>
        <template #body-cell-packaging="props">
          <q-td auto-width>
            <q-badge color="primary">{{ props.row.package_type.name }}</q-badge>
          </q-td>
        </template>
        <template #body-cell-remaining="props">
          <q-td auto-width>
            <q-badge
              :color="props.row.remaining < props.row.package_type.count ? 'accent' : 'positive'"
              >{{ props.row.remaining }} / {{ props.row.package_type.count }}</q-badge
            >
          </q-td>
        </template>
      </q-table>
    </ForegroundPanel>
    <ForegroundPanel
      v-else
      class="flex-[5] grid content-center justify-center uppercase text-gray-5"
    >
      Vyberte skladové místo
    </ForegroundPanel>
  </MainLayout>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetWarehouseLocation,
  warehouseApiRoutesWarehouseGetWarehouses,
  type WarehouseItemSchema,
  type WarehouseLocationDetailSchema,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import MainLayout from '@/components/layout/MainLayout.vue'
import { useQueryWarehouse } from '@/composables/query/use-warehouse-query'
import { useLocalStorage } from '@vueuse/core'
import type { QTable, QTableColumn } from 'quasar'
import { computed, ref, watch } from 'vue'

const result = await warehouseApiRoutesWarehouseGetWarehouses()
const warehouses = ref(result.data?.data ?? [])

const simple = computed(() =>
  warehouses.value.map((war) => {
    return {
      label: war.name,
      icon: 'sym_o_home_work',
      children: war.locations.map((loc) => ({ label: loc.code, icon: 'sym_o_pin_drop' })),
    }
  }),
)

const { location } = useQueryWarehouse()

const fetchWarehouseLocation = async () => {
  if (!location.value) {
    warehouseLocation.value = undefined
    return
  }
  const res = await warehouseApiRoutesWarehouseGetWarehouseLocation({
    path: { warehouse_location_code: location.value },
  })
  if (res.data?.data) {
    warehouseLocation.value = res.data.data
  }
}
const warehouseLocation = ref<WarehouseLocationDetailSchema>()
if (location.value) {
  await fetchWarehouseLocation()
}

watch(location, fetchWarehouseLocation)

interface WarehouseItemSchemaWithCount extends WarehouseItemSchema {
  itemsCount: number
}

const columns = ref<QTableColumn[]>([
  {
    field: (item: WarehouseItemSchema) => item.stock_item.name,
    name: 'name',
    label: 'Název',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.stock_item.code,
    name: 'code',
    label: 'Kód',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.package_type.name,
    name: 'packaging',
    label: 'Balení',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.remaining,
    name: 'remaining',
    label: 'Počet v balení',
    align: 'left' as const,
    sortable: true,
  },
])

const aggregate = useLocalStorage('aggragate-package-types', true)
const rows = computed(() => {
  if (aggregate.value) {
    return Object.values(
      (warehouseLocation.value?.items ?? []).reduce(
        (acc, item) => {
          const key = `${item.package_type.name}_${item.remaining}`

          if (!acc[key]) {
            acc[key] = {
              ...item,
              itemsCount: 1,
            }
          } else {
            acc[key].itemsCount += 1
          }

          return acc
        },
        {} as Record<string, WarehouseItemSchemaWithCount>,
      ),
    )
  }

  return warehouseLocation.value?.items ?? []
})

watch(
  aggregate,
  (value) => {
    if (value) {
      columns.value = [
        ...columns.value,
        {
          field: (item: WarehouseItemSchemaWithCount) => item.itemsCount,
          name: 'totalCount',
          label: 'Kusů balení',
          sortable: true,
          align: 'left',
        },
      ] as QTableColumn[]
    } else {
      columns.value = columns.value.filter((col) => col.name !== 'totalCount')
    }
  },
  { immediate: true },
)
</script>

<style></style>
