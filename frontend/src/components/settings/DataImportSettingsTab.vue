<template>
  <div>
    <h1 class="mb-2">IMPORT DAT</h1>
    <p class="mb-5 text-muted max-w-3xl">
      Jednorázový import dat ze starého systému. Import probíhá na pozadí v pořadí produkty, zákazníci,
      sklady a je atomický - při chybě se neuloží nic. Průběh můžete sledovat i po obnovení stránky.
    </p>

    <div class="flex flex-col gap-8 max-w-5xl">
      <section class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold uppercase">Produkty</h2>
        <JsonFileInput
          v-model="state.productsFile"
          label="Soubor s produkty"
          hint="JSON export produktů"
          :disable="running"
        />
      </section>

      <section class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold uppercase">Zákazníci</h2>
        <JsonFileInput
          v-model="state.customersFile"
          label="Soubor se zákazníky"
          hint="JSON export zákazníků včetně kontaktních osob"
          :disable="running"
        />
      </section>

      <section>
        <q-expansion-item
          v-model="warehousesExpanded"
          icon="sym_o_warehouse"
          label="Sklady a skladové zásoby"
          :caption="warehousesCaption"
          header-class="text-lg font-semibold uppercase"
          class="border rounded-md overflow-hidden"
        >
          <div class="p-4 flex flex-col gap-4">
            <p v-if="!state.warehouseRows.length" class="text-muted">Žádný sklad nebyl přidán.</p>
            <WarehouseImportRow
              v-for="(row, index) in state.warehouseRows"
              :key="row.key"
              v-model="state.warehouseRows[index]!"
              :disable="running"
              @remove="removeRow(index)"
            />
            <div>
              <q-btn
                flat
                color="primary"
                icon="add"
                label="přidat sklad"
                :disable="running"
                @click="addRow"
              />
            </div>
          </div>
        </q-expansion-item>
      </section>

      <div class="flex items-center gap-4">
        <q-btn
          color="primary"
          unelevated
          icon="sym_o_upload"
          label="importovat"
          :loading="running"
          :disable="!canSubmit || running"
          @click="submit"
        />
        <span v-if="incomplete" class="text-sm text-negative">
          Každý řádek skladu musí mít vyplněný název i soubor.
        </span>
      </div>

      <DataImportProgress v-if="status && status.state !== 'succeeded'" :status="status" @stop="stopWatching" />
      <DataImportResult v-if="status?.state === 'succeeded' && status.result" :result="status.result" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDataImportJob } from '@/composables/use-data-import-job'
import { computed, reactive, ref } from 'vue'
import DataImportProgress from './data-import/DataImportProgress.vue'
import DataImportResult from './data-import/DataImportResult.vue'
import JsonFileInput from './data-import/JsonFileInput.vue'
import WarehouseImportRow from './data-import/WarehouseImportRow.vue'
import {
  canSubmitDataImport,
  hasIncompleteRows,
  toDataImportBody,
  type DataImportFormState,
} from './data-import/data-import-body'

const { status, running, start, stopWatching } = useDataImportJob()

const state = reactive<DataImportFormState>({
  productsFile: null,
  customersFile: null,
  warehouseRows: [],
})
const warehousesExpanded = ref(false)
let nextKey = 0

const canSubmit = computed(() => canSubmitDataImport(state))
const incomplete = computed(() => hasIncompleteRows(state.warehouseRows))
const warehousesCaption = computed(() => {
  const count = state.warehouseRows.length
  return count ? `Počet skladů k importu: ${count}` : 'Volitelné'
})

const addRow = () => {
  state.warehouseRows.push({ key: nextKey++, warehouse: '', file: null })
}

const removeRow = (index: number) => {
  state.warehouseRows.splice(index, 1)
}

const submit = () => start(toDataImportBody(state))
</script>
