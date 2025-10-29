<template>
  <MainLayout>
    <div class="flex-1">
      <q-table
        :rows="products"
        :columns="columns"
        :loading="loading"
        flat
        v-model:pagination="pagination"
        no-data-label="Žádné produkty nenalezeny"
        :rows-per-page-options="[30, 50, 100]"
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
            <span class="flex items-center gap-1">
              <ProductTypeIcon :type="props.row.type" />
              {{ props.row.type }}
            </span>
          </q-td>
        </template>
      </q-table>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProducts, type ProductSchema } from '@/client'
import MainLayout from '@/components/layout/MainLayout.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'

const { page, pageSize, search } = useQueryProducts()

const pagination = ref<QTableProps['pagination']>({
  rowsPerPage: pageSize.value,
  page: page.value,
})

const products = ref<ProductSchema[]>([])
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
    products.value = res.data?.data ?? []
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchProducts)

watch(pagination, () => {
  if (pagination.value?.rowsPerPage === pageSize.value && pagination.value.page === page.value) {
    return
  }
  page.value = pagination.value?.page ?? 1
  pageSize.value = pagination.value?.rowsPerPage ?? 50
  fetchProducts()
})

watch(search, () => {
  fetchProducts()
})

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
]
</script>

<style lang="scss" scoped></style>
