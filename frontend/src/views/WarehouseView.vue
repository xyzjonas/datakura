<template>
  <ForegroundPanel class="min-w-[312px]">
    <div class="flex flex-col items-start">
      <SearchInput
        v-model="locationSearch"
        placeholder="Vyhledat skladové místo"
        clearable
        class="w-full"
      />
      <q-toggle v-model="showEmpty" size="sm"
        ><span class="text-xs">Zobrazit prazdná místa</span></q-toggle
      >
    </div>
    <q-separator></q-separator>
    <q-tree :nodes="simple" node-key="label" selected-color="primary" ref="tree">
      <template v-slot:default-header="prop">
        <div
          @click="setLocation(prop.node)"
          :class="
            prop.node.isPlace
              ? 'flex items-center cursor-pointer light:hover:bg-gray-1 dark:hover:bg-dark px-2 pr-4 rounded'
              : ''
          "
        >
          <q-icon :name="prop.node.icon" class="mr-2" color="gray-5" size="18px" />
          <span :class="{ 'font-bold text-primary': location === prop.node.label }">
            {{ prop.node.label }}
          </span>
          <span v-if="prop.node.count" class="ml-1 text-gray-5">
            - {{ prop.node.count }} {{ getProductsDeclention(prop.node.count) }}
          </span>
        </div>
      </template>
    </q-tree>
  </ForegroundPanel>

  <ForegroundPanel class="flex-[5]" v-if="warehouseLocation">
    <div class="flex justify-start items-center mb-2 gap-3">
      <h2>{{ warehouseLocation.code }}</h2>
      <q-badge v-if="warehouseLocation.is_putaway" color="accent">příjem</q-badge>
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
                params: { productCode: props.row.product.code },
              })
            "
            class="link"
            >{{ props.row.product.name }}</a
          >
        </q-td>
      </template>
      <template #body-cell-totalCount="props" v-if="aggregate">
        <q-td auto-width> {{ props.row.itemsCount }} ks </q-td>
      </template>
      <template #body-cell-packaging="props">
        <q-td auto-width>
          <PackageTypeBadge :package-type="props.row.package?.type" />
        </q-td>
      </template>
      <template #body-cell-remaining="props">
        <q-td auto-width>
          <WarehouseItemCountBadge :item="props.row" />
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
  <ForegroundPanel v-else class="flex-[5] grid content-center justify-center uppercase text-gray-5">
    Vyberte skladové místo
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetWarehouseLocation,
  warehouseApiRoutesWarehouseGetWarehouses,
  type WarehouseItemSchema,
  type WarehouseLocationDetailSchema,
  type WarehouseLocationSchema,
} from '@/client'
import EmptyPanel from '@/components/EmptyPanel.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import PackageTypeBadge from '@/components/PackageTypeBadge.vue'
import WarehouseItemCountBadge from '@/components/product/WarehouseItemCountBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryWarehouse } from '@/composables/query/use-warehouse-query'
import { useApi } from '@/composables/use-api'
import { aggregatePackaging } from '@/utils/aggregatePackaging'
import { useLocalStorage, useWindowScroll } from '@vueuse/core'
import { QTree, type QTable, type QTableColumn } from 'quasar'
import { computed, onMounted, ref, watch } from 'vue'

const { onResponse } = useApi()

const result = await warehouseApiRoutesWarehouseGetWarehouses()
const data = onResponse(result)
const warehouses = ref(data?.data ?? [])

const { location, locationSearch, itemSearch } = useQueryWarehouse()

const LOCATION_ICON = 'sym_o_pin_drop'

const tree = ref<QTree | null>(null)
type TreeElement = {
  label: string
  icon: string
  isPlace?: boolean
  children?: TreeElement[]
  count: number
}

const getLocationIcon = (location: WarehouseLocationSchema) => {
  if (location.is_putaway) {
    return 'sym_o_activity_zone'
  }
  return LOCATION_ICON
}

const showEmpty = ref(false)
const simple = computed(() =>
  warehouses.value.map((war) => {
    return {
      label: war.name,
      icon: 'sym_o_home_work',
      children: war.locations
        .filter((loc) => loc.code.toLowerCase().includes(locationSearch.value.toLowerCase()))
        .filter((loc) => (showEmpty.value ? true : loc.count > 0))
        .map((loc) => ({
          label: loc.code,
          icon: getLocationIcon(loc),
          isPlace: true,
          count: loc.count,
        })) as TreeElement[],
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
  const response = await warehouseApiRoutesWarehouseGetWarehouseLocation({
    path: { warehouse_location_code: location.value },
  })
  const data = onResponse(response)
  if (data) {
    warehouseLocation.value = data.data
  }
}
const warehouseLocation = ref<WarehouseLocationDetailSchema>()
if (location.value) {
  await fetchWarehouseLocation()
}

const { y } = useWindowScroll({ behavior: 'smooth' })
const setLocation = (element: TreeElement) => {
  if (element.isPlace) {
    location.value = element.label
    y.value = 0
  }
}

watch(location, fetchWarehouseLocation)

interface WarehouseItemSchemaWithCount extends WarehouseItemSchema {
  itemsCount: number
}

const columns = computed<QTableColumn[]>(() => {
  if (aggregate.value) {
    return [
      {
        field: (item: WarehouseItemSchema) => item.product.name,
        name: 'name',
        label: 'Název produktu',
        align: 'left' as const,
        sortable: true,
      },
      {
        field: (item: WarehouseItemSchema) => item.product.code,
        name: 'code',
        label: 'Kód produktu',
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
        field: (item: WarehouseItemSchema) => item.amount,
        name: 'remaining',
        label: 'Počet celkem',
        align: 'left' as const,
        sortable: true,
      },
      {
        field: (item: WarehouseItemSchemaWithCount) => item.itemsCount,
        name: 'totalCount',
        label: 'Kusů balení',
        sortable: true,
        align: 'left',
      },
    ]
  } else {
    return [
      {
        field: (item: WarehouseItemSchema) => item.product.name,
        name: 'name',
        label: 'Název produktu',
        align: 'left' as const,
        sortable: true,
      },
      {
        field: (item: WarehouseItemSchema) => item.product.code,
        name: 'code',
        label: 'Kód produktu',
        align: 'left' as const,
        sortable: true,
      },
      {
        field: (item: WarehouseItemSchema) => item.primary_barcode,
        name: 'code',
        label: 'EAN skladové položky',
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
        field: (item: WarehouseItemSchema) => item.amount,
        name: 'remaining',
        label: 'Počet v balení',
        align: 'left' as const,
        sortable: true,
      },
    ]
  }
})

const aggregate = useLocalStorage('aggragate-package-types', true)

const locationItems = computed(() =>
  (warehouseLocation.value?.items ?? []).filter(
    (item) =>
      item.product.code.toLowerCase().includes(itemSearch.value.toLowerCase()) ||
      item.product.name.toLowerCase().includes(itemSearch.value.toLowerCase()),
  ),
)

const rows = computed(() => {
  if (aggregate.value) {
    return aggregatePackaging(locationItems.value)
  }

  return locationItems.value
})

// watch(
//   aggregate,
//   (value) => {
//     if (value) {
//       columns.value = [
//         ...columns.value,
//         {
//           field: (item: WarehouseItemSchemaWithCount) => item.itemsCount,
//           name: 'totalCount',
//           label: 'Kusů balení',
//           sortable: true,
//           align: 'left',
//         },
//       ] as QTableColumn[]
//     } else {
//       columns.value = columns.value.filter((col) => col.name !== 'totalCount')
//     }
//   },
//   { immediate: true },
// )

const getProductsDeclention = (amount: number) => {
  if (amount === 1) {
    return 'produkt'
  }
  if (amount > 1 && amount < 5) {
    return 'produkty'
  }
  return 'produktů'
}
</script>

<style></style>
