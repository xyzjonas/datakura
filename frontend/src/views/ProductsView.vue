<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled Produktů</h1>
        <h5 class="text-gray-5 mt-2">Správa evidovaných produktů</h5>
      </div>
      <q-btn color="primary" unelevated label="vytvořit" icon="sym_o_add" @click="openCreateForm" />
    </div>
    <q-table
      :rows="products"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné produkty nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat položku"
          clearable
          :debounce="300"
        ></SearchInput>
      </template>
      <template #body-cell-name="props">
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
      </template>
      <template #body-cell-type="props">
        <q-td auto-width>
          <span class="flex items-center gap-1 flex-nowrap">
            <ProductTypeIcon :type="props.row.type" />
            {{ props.row.type }}
          </span>
        </q-td>
      </template>
    </q-table>

    <ProductUpsertDialog
      v-model:show="showCreateDialog"
      v-model="productForm"
      title="Vytvořit produkt"
      submit-label="vytvořit"
      :loading="creating"
      @submit="createProduct"
    />
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductCreateProduct,
  warehouseApiRoutesProductGetProducts,
  type ProductCreateOrUpdateSchema,
  type ProductSchema,
} from '@/client'
import ProductUpsertDialog from '@/components/product/ProductUpsertDialog.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search } = useQueryProducts()
const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const products = ref<ProductSchema[]>([])
const creating = ref(false)
const showCreateDialog = ref(false)

const createDefaultForm = (): ProductCreateOrUpdateSchema => ({
  name: '',
  code: '',
  type: '',
  unit: 'KS',
  group: '',
  unit_weight: 0,
  base_price: 0,
  purchase_price: 0,
  currency: 'CZK',
  customs_declaration_group: '',
  attributes: {},
})

const productForm = ref<ProductCreateOrUpdateSchema>(createDefaultForm())

const openCreateForm = () => {
  productForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const createProduct = async (body: ProductCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesProductCreateProduct({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchProducts()
    }
  } finally {
    creating.value = false
  }
}

const loading = ref(false)
const fetchProducts = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesProductGetProducts({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      products.value = res.data.data
      pagination.value.rowsNumber = res.data.count
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchProducts)

const shouldNotFetch = () => {
  return pagination.value.rowsPerPage === pageSize.value && pagination.value.page === page.value
}

const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
  if (!requestProp.pagination) {
    return
  }
  pagination.value = requestProp.pagination
  if (shouldNotFetch()) {
    return
  }
  page.value = Number(pagination.value.page)
  setTimeout(() => (pageSize.value = Number(pagination.value.rowsPerPage)), 1)
  setTimeout(() => fetchProducts(), 2)
}

const { currentRoute } = useRouter()
watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetchProducts()
  }
})

watch(search, fetchProducts)

const columns: QTableColumn[] = [
  {
    name: 'name',
    field: 'name',
    label: 'Název',
    align: 'left',
  },
  {
    name: 'code',
    field: 'code',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'group',
    field: 'group',
    label: 'Skupina',
    align: 'left',
  },
  {
    name: 'type',
    field: 'type',
    label: 'Typ zboží',
    align: 'left',
  },
  {
    name: 'unit',
    field: 'unit',
    label: 'Jednotka',
    align: 'right',
  },
  {
    name: 'purchase_price',
    field: (item: ProductSchema) =>
      item.purchase_price ? `${item.purchase_price} ${item.currency}` : '-',
    label: 'Nákupní cena',
    align: 'right',
  },
  {
    name: 'base_price',
    label: 'Prodejní cena',
    align: 'right',
    field: (item: ProductSchema) => (item.base_price ? `${item.base_price} ${item.currency}` : '-'),
  },
]
</script>

<style lang="scss" scoped></style>
