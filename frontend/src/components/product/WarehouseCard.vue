<template>
  <ForegroundPanel class="min-w-[256px]">
    <SearchInput
      v-model="locationSearch"
      placeholder="Vyhledat skladové místo"
      clearable
      class="mb-4"
    />
    <q-tree
      :nodes="simple"
      node-key="label"
      selected-color="primary"
      ref="tree"
      default-expand-all
      no-nodes-label="Žádná skladová místa"
    >
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
          <span class="font-thin">{{ prop.node.count.toFixed(2) }}</span>
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
          <h2 class="font-thin">{{ warehouseLocationCount?.toFixed(2) }}</h2>
          <span class="font-thin text-[10px] text-gray-5">{{ productUnit }}</span>
        </span>
      </div>
      <q-btn
        flat
        label="detail skladového místa"
        :to="{
          name: 'warehouses',
          query: { location: warehouseLocation.code, locationSearch: warehouseLocation.code },
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
          <PackageTypeBadge :package-type="props.value" />
        </q-td>
      </template>
      <template #body-cell-remaining="props">
        <q-td auto-width>
          <WarehouseItemCountBadge :item="props.row" />
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
import { aggregatePackaging, type WarehouseItemSchemaWithCount } from '@/utils/aggregatePackaging'
import WarehouseItemCountBadge from './WarehouseItemCountBadge.vue'
import { useApi } from '@/composables/use-api'
import PackageTypeBadge from '../PackageTypeBadge.vue'

const { onResponse } = useApi()

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
const data = onResponse(res)
const warehouses = data?.data ?? []

const simple = computed(() =>
  warehouses.map((war) => {
    return {
      label: war.name,
      icon: 'sym_o_home_work',
      count: war.locations
        .map((loc) => loc.items.reduce((a, b) => a + b.amount, 0))
        .reduce((a, b) => a + b, 0),
      children: war.locations
        .filter((loc) => loc.code.toLowerCase().includes(locationSearch.value.toLowerCase()))
        .map((loc) => ({
          label: loc.code,
          icon: LOCATION_ICON,
          parent: war.name,
          count: loc.items.reduce((a, b) => a + b.amount, 0),
        })) as TreeElement[],
    }
  }),
)

const warehouseLocation = ref<WarehouseLocationDetailSchema>()
const warehouseLocationCount = computed(() => {
  if (warehouseLocation.value) {
    return warehouseLocation.value.items.reduce((a, b) => a + b.amount, 0)
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

const columns = ref<QTableColumn[]>([])

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

watch(
  aggregate,
  (value) => {
    if (value) {
      columns.value = [
        {
          field: (item: WarehouseItemSchema) => item.package?.type,
          name: 'packaging',
          label: 'Balení',
          align: 'left' as const,
          sortable: true,
        },
        {
          field: (item: WarehouseItemSchemaWithCount) =>
            item.package?.type ? item.itemsCount : '-',
          name: 'totalCount',
          label: 'Kusů balení',
          sortable: true,
          align: 'left',
        },
        {
          field: (item: WarehouseItemSchema) =>
            item.package ? `${item.package.amount} × ${item.unit_of_measure}` : '-',
          name: 'packagingSize',
          label: 'Velikost balení',
          align: 'right',
          sortable: true,
        },
        {
          field: (item: WarehouseItemSchema) => item.amount,
          name: 'remaining',
          label: 'Počet MJ',
          align: 'left',
          sortable: true,
        },
      ] as QTableColumn[]
    } else {
      columns.value = [
        {
          field: (item: WarehouseItemSchema) => item.package?.type,
          name: 'packaging',
          label: 'Balení',
          align: 'left' as const,
          sortable: true,
        },
        {
          field: (item: WarehouseItemSchema) => item.code,
          name: 'code',
          label: 'Kód',
          align: 'left' as const,
          sortable: true,
        },
        {
          field: (item: WarehouseItemSchema) => item.amount,
          name: 'remaining',
          label: 'Počet MJ',
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
