<template>
  <MainLayout>
    <ForegroundPanel class="min-w-[256px]">
      <SearchInput
        v-model="locationSearch"
        placeholder="Vyhledat skladové místo"
        clearable
        class="mb-4"
      />
      <q-tree :nodes="simple" node-key="label" selected-color="primary" ref="tree">
        <template v-slot:default-header="prop">
          <div
            @click="setLocation(prop.node)"
            :class="
              prop.node.icon === LOCATION_ICON
                ? 'flex items-center cursor-pointer light:hover:bg-gray-1 dark:hover:bg-dark px-2 pr-4 rounded'
                : ''
            "
          >
            <q-icon :name="prop.node.icon" class="mr-2" color="gray-5" size="18px" />
            <span :class="{ 'font-bold text-primary': location === prop.node.label }">{{
              prop.node.label
            }}</span>
          </div>
        </template>
      </q-tree>
    </ForegroundPanel>

    <ForegroundPanel class="flex-[5]" v-if="warehouseLocation">
      <div class="flex justify-between items-center">
        <h2 class="mb-5">{{ warehouseLocation.code }}</h2>
      </div>

      <q-table
        :rows="rows"
        :columns="columns"
        flat
        :pagination="{ rowsPerPage: 20 }"
        class="bg-transparent"
      >
        <template #top-right>
          <SearchInput v-model="itemSearch" placeholder="Vyhledat položku" clearable></SearchInput>
        </template>
        <template #top-left>
          <q-toggle v-model="aggregate">
            <span class="text-slate"> Sloučit podle typu balení </span>
          </q-toggle>
        </template>
        <template #body-cell-name="props">
          <q-td>
            <a
              @click="
                $router.push({
                  name: 'productDetail',
                  params: { productCode: props.row.stock_item.code },
                })
              "
              class="link"
              >{{ props.row.stock_item.name }}</a
            >
          </q-td>
        </template>
        <template #body-cell-totalCount="props" v-if="aggregate">
          <q-td auto-width> {{ props.row.itemsCount }} ks </q-td>
        </template>
        <template #body-cell-packaging="props">
          <q-td auto-width>
            <q-badge color="primary">{{ props.row.unit_of_measure }}</q-badge>
          </q-td>
        </template>
        <template #body-cell-remaining="props">
          <q-td auto-width>
            <q-badge
              :color="props.row.remaining < props.row.factor_at_receipt ? 'accent' : 'positive'"
              >{{ props.row.remaining }} / {{ props.row.factor_at_receipt }}</q-badge
            >
          </q-td>
        </template>
        <template #no-data>
          <EmptyPanel
            text="Žádné skladové položky"
            icon="sym_o_search_off"
            class="w-full h-lg mt-2"
          />
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
import EmptyPanel from '@/components/EmptyPanel.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import MainLayout from '@/components/layout/MainLayout.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryWarehouse } from '@/composables/query/use-warehouse-query'
import { useLocalStorage, useWindowScroll } from '@vueuse/core'
import { QTree, type QTable, type QTableColumn } from 'quasar'
import { computed, onMounted, ref, watch } from 'vue'

const result = await warehouseApiRoutesWarehouseGetWarehouses()
const warehouses = ref(result.data?.data ?? [])

const { location, locationSearch, itemSearch } = useQueryWarehouse()

const LOCATION_ICON = 'sym_o_pin_drop'

const tree = ref<QTree | null>(null)
type TreeElement = {
  label: string
  icon: string
  children?: TreeElement[]
}

const simple = computed(() =>
  warehouses.value.map((war) => {
    return {
      label: war.name,
      icon: 'sym_o_home_work',
      children: war.locations
        .filter((loc) => loc.code.toLowerCase().includes(locationSearch.value.toLowerCase()))
        .map((loc) => ({ label: loc.code, icon: LOCATION_ICON })) as TreeElement[],
    }
  }),
)

const collapseTree = () => {
  if (!tree.value) {
    return
  }
  if (locationSearch.value) {
    tree.value.expandAll()
  } else {
    tree.value.collapseAll()
  }
}

watch(locationSearch, collapseTree, { immediate: true })

onMounted(collapseTree)

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

const { y } = useWindowScroll({ behavior: 'smooth' })
const setLocation = (element: TreeElement) => {
  if (element.icon === LOCATION_ICON) {
    location.value = element.label
    y.value = 0
  }
}

watch(location, fetchWarehouseLocation)

interface WarehouseItemSchemaWithCount extends WarehouseItemSchema {
  itemsCount: number
}

const columns = ref<QTableColumn[]>([
  {
    field: (item: WarehouseItemSchema) => item.stock_item.name,
    name: 'name',
    label: 'Název produktu',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.stock_item.code,
    name: 'code',
    label: 'Kód produktu',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.code,
    name: 'code',
    label: 'Kód skladové položky',
    align: 'left' as const,
    sortable: true,
  },
  {
    field: (item: WarehouseItemSchema) => item.unit_of_measure,
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

const locationItems = computed(() =>
  (warehouseLocation.value?.items ?? []).filter(
    (item) =>
      item.stock_item.code.toLowerCase().includes(itemSearch.value.toLowerCase()) ||
      item.stock_item.name.toLowerCase().includes(itemSearch.value.toLowerCase()),
  ),
)

const rows = computed(() => {
  if (aggregate.value) {
    return Object.values(
      locationItems.value.reduce(
        (acc, item) => {
          const key = `${item.unit_of_measure}_${item.remaining}`

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

  return locationItems.value
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
