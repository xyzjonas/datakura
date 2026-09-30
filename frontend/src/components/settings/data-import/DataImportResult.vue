<template>
  <q-card flat bordered class="rounded-md">
    <div class="p-4 flex flex-col gap-3">
      <h2 class="text-lg font-semibold uppercase">Výsledek importu</h2>

      <div v-if="result.products" class="flex flex-col gap-1" data-test="result-products">
        <strong>Produkty</strong>
        <span>
          vytvořeno {{ result.products.created }}, aktualizováno {{ result.products.updated }},
          přeskočeno {{ result.products.skipped }}, čárových kódů
          {{ result.products.barcodes_attached }}
        </span>
      </div>

      <div v-if="result.customers" class="flex flex-col gap-1" data-test="result-customers">
        <strong>Zákazníci</strong>
        <span>
          vytvořeno {{ result.customers.created }}, aktualizováno {{ result.customers.updated }},
          kontaktních osob {{ result.customers.contacts }}, nových skupin
          {{ result.customers.groups_created }}
        </span>
      </div>

      <div
        v-for="warehouse in result.warehouses"
        :key="warehouse.warehouse"
        class="flex flex-col gap-1"
        data-test="result-warehouse"
      >
        <strong>
          Sklad {{ warehouse.warehouse }}
          <q-badge v-if="warehouse.warehouse_created" color="positive" label="nový" />
        </strong>
        <span>
          položek {{ warehouse.items_created }}, nových lokací {{ warehouse.locations_created }},
          použitých lokací {{ warehouse.locations_existing }}
        </span>
      </div>

      <q-banner v-if="warnings.length" rounded class="bg-warning/20" data-test="result-warnings">
        <div v-for="(warning, index) in warnings" :key="index" class="text-sm">
          {{ warning }}
        </div>
      </q-banner>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import type { DataImportResultSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ result: DataImportResultSchema }>()

const warnings = computed(() => [
  ...(props.result.products?.warnings ?? []),
  ...(props.result.customers?.warnings ?? []),
])
</script>
