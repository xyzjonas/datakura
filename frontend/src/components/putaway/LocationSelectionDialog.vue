<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-xl">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center gap-2">
          <span class="text-2xl uppercase">Vybrat skladové místo</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <span class="text-xl text-gray-5">{{ item.product.name }}</span>
        <q-form class="flex flex-col gap-2" @submit="onConfirm">
          <q-separator class="my-5"></q-separator>
          <h2 class="text-lg">Skladová místa kde se tato položka již nachází</h2>
          <q-list separator class="mt-3" v-if="locationsWithTheSameProduct.length > 0">
            <q-item
              v-for="location in locationsWithTheSameProduct"
              :key="location.code"
              clickable
              v-ripple
              @click="selectedLocation = location"
              :active="selectedLocation?.code === location.code"
              active-class="bg-blue-1"
            >
              <q-item-section>{{ location.code }}</q-item-section>
              <q-item-section>{{ location.warehouse_name }}</q-item-section>
              <q-item-section avatar>
                <q-icon v-if="location.is_putaway" name="sym_o_crop_free" size="18px">
                  <q-tooltip>Toto skladové místo je určeno pro příjem</q-tooltip>
                </q-icon>
              </q-item-section>
            </q-item>
          </q-list>
          <empty-panel v-else class="py-5">Položka není skladem</empty-panel>

          <q-separator class="my-5"></q-separator>
          <h2 class="text-lg">Vyhledat skladové místo</h2>

          <q-input
            outlined
            v-model="search"
            label="Kód skladového místa"
            hint="Vyhledejte skladové místo podle kódu"
            class="mt-5"
            @update:model-value="debouncedSearch"
            :debounce="300"
            :loading="loading"
          ></q-input>

          <q-list separator class="mt-3">
            <q-item
              v-for="location in locations"
              :key="location.code"
              clickable
              v-ripple
              @click="selectedLocation = location"
              :active="selectedLocation?.code === location.code"
              active-class="bg-blue-1"
            >
              <q-item-section>{{ location.code }}</q-item-section>
              <q-item-section>{{ location.warehouse_name }}</q-item-section>
              <q-item-section avatar>
                <q-icon v-if="location.is_putaway" name="sym_o_crop_free" size="18px">
                  <q-tooltip>Toto skladové místo je určeno pro příjem</q-tooltip>
                </q-icon>
              </q-item-section>
            </q-item>
          </q-list>

          <q-btn
            type="submit"
            unelevated
            color="primary"
            label="Potvrdit"
            class="h-[3rem] mt-3"
            :disable="!selectedLocation"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetWarehouseLocations,
  type WarehouseItemSchema,
  type WarehouseLocationSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { onMounted, ref, watch } from 'vue'
import EmptyPanel from '../EmptyPanel.vue'

const { onResponse } = useApi()

const props = defineProps<{ item: WarehouseItemSchema }>()

const showDialog = defineModel('show', { default: false })
const search = ref('')
const locations = ref<WarehouseLocationSchema[]>([])
const selectedLocation = ref<WarehouseLocationSchema | null>(null)
const page = ref(1)

const PAGE_SIZE = 5

const emit = defineEmits<{
  (e: 'confirm', location: WarehouseLocationSchema): void
}>()

const loading = ref(false)

const locationsWithTheSameProduct = ref<WarehouseLocationSchema[]>([])
onMounted(async () => {
  loading.value = true
  const result = await warehouseApiRoutesWarehouseGetWarehouseLocations({
    query: {
      page_size: 200,
      stock_product_code: props.item.product.code,
    },
  })
  const data = onResponse(result)
  if (data) {
    locationsWithTheSameProduct.value = data.data
  }
  setTimeout(() => (loading.value = false), 300)
})

const fetchLocations = async () => {
  loading.value = true
  const result = await warehouseApiRoutesWarehouseGetWarehouseLocations({
    query: {
      page: page.value,
      search_term: search.value,
      page_size: PAGE_SIZE,
    },
  })
  const data = onResponse(result)
  if (data) {
    locations.value = data.data
  }
  setTimeout(() => (loading.value = false), 300)
}

const debouncedSearch = () => {
  page.value = 1
  fetchLocations()
}

watch(showDialog, (newValue) => {
  if (newValue) {
    fetchLocations()
  }
})

const onConfirm = () => {
  if (selectedLocation.value) {
    emit('confirm', selectedLocation.value)
    showDialog.value = false
  }
}
</script>
