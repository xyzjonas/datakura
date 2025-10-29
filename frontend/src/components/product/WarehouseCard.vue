<template>
  <ForegroundPanel class="min-w-[256px]">
    <SearchInput
      v-model="locationSearch"
      placeholder="Vyhledat skladové místo"
      clearable
      class="mb-4"
    />
    <q-tree :nodes="simple" node-key="label" selected-color="primary" ref="tree" default-expand-all>
      <template v-slot:default-header="prop">
        <div
          @click="setLocation(prop.node)"
          :class="{
            'flex items-center cursor-pointer light:hover:bg-gray-1 dark:hover:bg-dark px-2 pr-4 rounded':
              prop.node.icon === LOCATION_ICON,
            'font-bold': warehouseLocation?.code === prop.node.label,
          }"
        >
          <q-icon :name="prop.node.icon" class="mr-2" color="gray-5" size="18px" />
          <span :class="{ 'font-bold text-red': location === prop.node.label }">{{
            prop.node.label
          }}</span>
          <span class="mx-2 font-thin text-gray-5">|</span>
          <span class="font-thin">{{ prop.node.count }}</span>
          <span class="ml-1 font-thin text-[10px] text-gray-5">{{ productUnit }}</span>
        </div>
      </template>
    </q-tree>
  </ForegroundPanel>

  <ForegroundPanel class="flex-[5]" v-if="warehouseLocation">
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-4">
        <h2>{{ warehouseLocation.code }}</h2>
        <q-separator vertical />
        <span class="flex items-center gap-1">
          <h2 class="font-thin">{{ warehouseLocationCount }}</h2>
          <span class="font-thin text-[10px] text-gray-5">{{ productUnit }}</span>
        </span>
      </div>
      <q-btn
        flat
        label="detail skladového místa"
        :to="{
          name: 'warehouse',
          query: { location: warehouseLocation.code, locationSearch: 'AA-01-01' },
        }"
        icon-right="sym_o_jump_to_element"
      />
    </div>

    <q-table
      :rows="rows"
      :columns="columns"
      flat
      :pagination="{ rowsPerPage: 20 }"
      class="bg-transparent"
    >
      <template #top-left>
        <q-toggle v-model="aggregate">
          <span class="text-slate"> Sloučit podle typu balení </span>
        </q-toggle>
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
    </q-table>
  </ForegroundPanel>
  <ForegroundPanel v-else class="flex-[5] grid content-center justify-center uppercase text-gray-5">
    Vyberte skladové místo
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { useQueryProduct } from '@/composables/query/use-product-query'
import ForegroundPanel from '../ForegroundPanel.vue'
import SearchInput from '../SearchInput.vue'
import { computed, ref, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import type { QTableColumn, QTree } from 'quasar'
import {
  warehouseApiRoutesProductGetProductWarehouseInfo,
  type WarehouseItemSchema,
  type WarehouseLocationDetailSchema,
} from '@/client'

const props = defineProps<{ productCode: string; productUnit: string }>()

const { locationSearch, itemSearch } = useQueryProduct()
const aggregate = useLocalStorage('product-detail-aggregate', false)

const LOCATION_ICON = 'sym_o_pin_drop'

const location = ref()
const tree = ref<QTree | null>(null)
type TreeElement = {
  label: string
  icon: string
  parent?: string
  children?: TreeElement[]
}

const res = await warehouseApiRoutesProductGetProductWarehouseInfo({
  path: { product_code: props.productCode },
})
const warehouses = res.data?.data ?? []

const simple = computed(() =>
  warehouses.map((war) => {
    return {
      label: war.name,
      icon: 'sym_o_home_work',
      count: war.locations
        .map((loc) => loc.items.reduce((a, b) => a + b.remaining, 0))
        .reduce((a, b) => a + b, 0),
      children: war.locations
        .filter((loc) => loc.code.toLowerCase().includes(locationSearch.value.toLowerCase()))
        .map((loc) => ({
          label: loc.code,
          icon: LOCATION_ICON,
          parent: war.name,
          count: loc.items.reduce((a, b) => a + b.remaining, 0),
        })) as TreeElement[],
    }
  }),
)

const warehouseLocation = ref<WarehouseLocationDetailSchema>()
const warehouseLocationCount = computed(() => {
  if (warehouseLocation.value) {
    return warehouseLocation.value.items.reduce((a, b) => a + b.remaining, 0)
  }
  return undefined
})
if (warehouses[0] && warehouses[0].locations.length > 0) {
  warehouseLocation.value = warehouses[0].locations[0]
}

const setLocation = (element: TreeElement) => {
  if (element.icon === LOCATION_ICON) {
    const warehouse = warehouses.find((war) => war.name === element.parent)
    if (!warehouse) {
      return
    }

    const loc = warehouse.locations.find((loc) => loc.code === element.label)
    if (loc) {
      warehouseLocation.value = loc
    }
  }
}

interface WarehouseItemSchemaWithCount extends WarehouseItemSchema {
  itemsCount: number
}

const columns = ref<QTableColumn[]>([
  // {
  //   field: (item: WarehouseItemSchema) => item.stock_item.name,
  //   name: 'name',
  //   label: 'Název',
  //   align: 'left' as const,
  //   sortable: true,
  // },
  // {
  //   field: (item: WarehouseItemSchema) => item.code,
  //   name: 'code',
  //   label: 'Kód',
  //   align: 'left' as const,
  //   sortable: true,
  // },
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
          align: 'left',
          sortable: true,
        },
        {
          field: (item: WarehouseItemSchemaWithCount) => item.itemsCount,
          name: 'totalCount',
          label: 'Kusů balení',
          sortable: true,
          align: 'right' as const,
        },
      ] as QTableColumn[]
    } else {
      columns.value = [
        {
          field: (item: WarehouseItemSchema) => item.code,
          name: 'code',
          label: 'Kód',
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
      ]
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
