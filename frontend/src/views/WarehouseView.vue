<template>
  <MainLayout>
    <ForegroundPanel class="pr-10 flex-1">
      <q-tree
        :nodes="simple"
        node-key="label"
        selected-color="primary"
        v-model:selected="selected"
        default-expand-all
      />
    </ForegroundPanel>

    <ForegroundPanel class="flex-[5]">
      <div v-if="warehouseLocation">
        <h1 class="mb-5">{{ warehouseLocation.code }}</h1>
        <q-list separator dense>
          <q-item v-for="item in warehouseLocation.items" :key="item.stock_item.code">
            <q-item-section>
              <span class="flex items-center gap-2">
                {{ item.stock_item.name }}
                <q-separator vertical></q-separator>
                <q-badge>{{ item.package_type.name }}</q-badge>
                <q-badge
                  :color="item.remaining < item.package_type.count ? 'accent' : 'positive'"
                  class="ml-auto"
                  >{{ item.remaining }} / {{ item.package_type.count }}</q-badge
                >
              </span>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </ForegroundPanel>
  </MainLayout>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetWarehouseLocation,
  warehouseApiRoutesWarehouseGetWarehouses,
  type WarehouseLocationDetailSchema,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import MainLayout from '@/components/layout/MainLayout.vue'
import { computed, ref, watch } from 'vue'

const selected = ref('')

const result = await warehouseApiRoutesWarehouseGetWarehouses()
const warehouses = ref(result.data?.data ?? [])

const simple = computed(() =>
  warehouses.value.map((war) => {
    return {
      label: war.name,
      children: war.locations.map((loc) => ({ label: loc.code })),
    }
  }),
)

const warehouseLocation = ref<WarehouseLocationDetailSchema>()
watch(selected, async (value: string) => {
  const res = await warehouseApiRoutesWarehouseGetWarehouseLocation({
    query: { warehouse_location_code: value },
  })
  if (res.data?.data) {
    warehouseLocation.value = res.data.data
  }
})
</script>

<style></style>
