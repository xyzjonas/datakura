<template>
  <div>
    <h1 class="mb-2">PŘIZPŮSOBENÍ APLIKACE</h1>
    <p class="mb-5 text-muted max-w-3xl">
      Nastavení ovládání aplikace pro aktuálního uživatele a výchozí tiskárny pro tisk dokladů.
    </p>

    <div class="flex flex-col gap-10">
      <section>
        <h2 class="text-lg font-semibold uppercase mb-3">Ovládání</h2>
        <q-list bordered separator class="rounded overflow-hidden">
          <q-item tag="label">
            <q-item-section>
              <q-item-label>Režim čtečky (scanner mode)</q-item-label>
              <q-item-label caption>
                Optimalizuje výběr skladové položky pro Zebra / ruční čtečku čárových kódů
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="scannerMode" color="primary" />
            </q-item-section>
          </q-item>
        </q-list>
        <div class="mt-3 ml-3 text-caption text-muted">
          Aktuální režim:
          <q-badge :color="scannerMode ? 'secondary' : 'primary'">
            {{ scannerMode ? 'čtečka' : 'webové rozhraní' }}
          </q-badge>
        </div>
      </section>

      <section>
        <h2 class="text-lg font-semibold uppercase mb-3">Výchozí tiskárna</h2>

        <q-card flat bordered class="rounded-md">
          <div class="p-4 flex flex-col gap-4">
            <div>
              <div class="mt-3 text-caption text-muted">
                Vybraná tiskárna:
                <q-badge :color="currentPrinter?.code ? 'primary' : 'grey-8'">
                  {{ currentPrinter?.code ?? 'nenastaveno' }}
                </q-badge>
              </div>
              <!-- <div class="font-medium">
                {{ currentPrinter?.code ?? 'Žádná tiskárna není přiřazena' }}
              </div> -->
              <div class="text-sm text-muted mt-1">
                {{
                  currentPrinter?.description ||
                  'Vyberte tiskárnu, která se má nabídnout jako výchozí při tisku.'
                }}
              </div>
            </div>

            <PrinterSelect
              :key="printerSelectKey"
              v-model="selectedPrinterCode"
              label="Přiřadit tiskárnu"
              hint="Lze vyhledat podle kódu nebo popisu"
            />

            <div class="flex flex-wrap gap-3 justify-end">
              <q-btn
                flat
                color="primary"
                icon="add"
                label="nová tiskárna"
                @click="openCreateDialog"
              />
              <q-btn
                v-if="currentPrinter"
                flat
                color="negative"
                icon="delete"
                label="odebrat přiřazení"
                :loading="savingDefaultPrinter"
                @click="clearDefaultPrinter"
              />
              <q-btn
                unelevated
                color="primary"
                icon="save"
                label="uložit výchozí tiskárnu"
                :loading="savingDefaultPrinter"
                :disable="!selectedPrinterCode || selectedPrinterCode === currentPrinter?.code"
                @click="saveDefaultPrinter"
              />
            </div>
          </div>
        </q-card>
      </section>
    </div>

    <PrinterUpsertDialog
      v-model:show="showCreateDialog"
      v-model="printerForm"
      title="Přidat tiskárnu"
      submit-label="přidat"
      :loading="creatingPrinter"
      @submit="createPrinter"
    />
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesAuthSetDefaultPrinter,
  warehouseApiRoutesPrintersCreatePrinter,
  type PrinterCreateOrUpdateSchema,
} from '@/client'
import PrinterSelect from '@/components/selects/PrinterSelect.vue'
import PrinterUpsertDialog from '@/components/settings/printers/PrinterUpsertDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppSettings } from '@/composables/use-app-settings'
import { useAuth } from '@/composables/use-auth'
import { computed, ref, watch } from 'vue'

const { scannerMode } = useAppSettings()
const { onResponse } = useApi()
const { user, whoami } = useAuth()

const selectedPrinterCode = ref<string | null>(null)
const printerSelectKey = ref(0)
const showCreateDialog = ref(false)
const savingDefaultPrinter = ref(false)
const creatingPrinter = ref(false)

const createDefaultPrinterForm = (): PrinterCreateOrUpdateSchema => ({
  code: '',
  description: null,
})

const printerForm = ref<PrinterCreateOrUpdateSchema>(createDefaultPrinterForm())

const currentPrinter = computed(() => user.value?.default_printer ?? null)

watch(
  currentPrinter,
  (printer) => {
    selectedPrinterCode.value = printer?.code ?? null
  },
  { immediate: true },
)

const openCreateDialog = () => {
  printerForm.value = createDefaultPrinterForm()
  showCreateDialog.value = true
}

const createPrinter = async (body: PrinterCreateOrUpdateSchema) => {
  creatingPrinter.value = true
  try {
    const result = await warehouseApiRoutesPrintersCreatePrinter({ body })
    const response = onResponse(result)
    if (response?.data) {
      selectedPrinterCode.value = response.data.code
      printerSelectKey.value += 1
      showCreateDialog.value = false
    }
  } finally {
    creatingPrinter.value = false
  }
}

const saveDefaultPrinter = async () => {
  savingDefaultPrinter.value = true
  try {
    const result = await warehouseApiRoutesAuthSetDefaultPrinter({
      body: { printer_code: selectedPrinterCode.value },
    })
    const response = onResponse(result)
    if (response) {
      await whoami()
    }
  } finally {
    savingDefaultPrinter.value = false
  }
}

const clearDefaultPrinter = async () => {
  selectedPrinterCode.value = null
  await saveDefaultPrinter()
}
</script>
