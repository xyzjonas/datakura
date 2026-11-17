<template>
  <q-card flat bordered class="rounded-md">
    <div class="p-4 flex flex-col gap-3">
      <p class="text-sm text-muted">
        Pokud je zisk položky nebo celé přijaté objednávky / nabídky nižší než tato hranice,
        zvýrazní se červeně a nahoře se zobrazí upozornění. Hranici lze zadat jako přirážku nebo
        marži - uložena je jedna hodnota. 0 = bez hlídání.
      </p>
      <q-btn-toggle
        v-model="basis"
        unelevated
        no-caps
        toggle-color="primary"
        :options="[
          { label: 'Přirážka', value: 'markup' },
          { label: 'Marže', value: 'margin' },
        ]"
        data-test="profit-basis"
      />
      <div class="flex items-center gap-3">
        <q-input
          v-model.number="input"
          type="number"
          outlined
          dense
          min="0"
          suffix="%"
          :label="basis === 'markup' ? 'Minimální přirážka' : 'Minimální marže'"
          class="w-64"
          hide-bottom-space
          :loading="loading"
          :error="!isValid"
          :error-message="
            basis === 'margin' ? 'Marže musí být 0 až méně než 100 %' : 'Neplatná hodnota'
          "
        />
        <q-btn
          unelevated
          color="primary"
          label="uložit"
          :loading="saving"
          :disable="!isValid || markup === savedMarkup"
          @click="save"
        />
      </div>
      <div v-if="isValid" class="text-sm text-muted" data-test="profit-equivalent">
        Odpovídá
        {{
          basis === 'markup'
            ? `marži ${format(markupToMargin(markup))} %`
            : `přirážce ${format(markup)} %`
        }}
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesSettingsGetGlobalSettings,
  warehouseApiRoutesSettingsUpdateGlobalSettings,
} from '@/client'
import { setMinimumMarkupPercent } from '@/composables/use-minimum-profit'
import { useApi } from '@/composables/use-api'
import { useQuasar } from 'quasar'
import { marginToMarkup, markupToMargin, type ProfitBasis } from '@/utils/minimum-profit'
import { computed, onMounted, ref, watch } from 'vue'

const { onResponse } = useApi()
const $q = useQuasar()

const basis = ref<ProfitBasis>('markup')
const input = ref(0)
const savedMarkup = ref(0)
const loading = ref(false)
const saving = ref(false)

const format = (value: number) => Number(value.toFixed(2))

const isValid = computed(() => {
  const value = input.value
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return false
  return basis.value === 'markup' || value < 100
})

// the stored (markup) value of what is currently typed in
const markup = computed(() => {
  if (!isValid.value) return savedMarkup.value
  return format(basis.value === 'markup' ? input.value : marginToMarkup(input.value))
})

// switching the way of thinking keeps the very same threshold
watch(basis, (next, previous) => {
  if (!isValid.value) return
  const asMarkup = previous === 'markup' ? input.value : marginToMarkup(input.value)
  input.value = format(next === 'markup' ? asMarkup : markupToMargin(asMarkup))
})

const apply = (value: number) => {
  savedMarkup.value = value
  input.value = format(basis.value === 'markup' ? value : markupToMargin(value))
  setMinimumMarkupPercent(value)
}

onMounted(async () => {
  loading.value = true
  try {
    const response = onResponse(await warehouseApiRoutesSettingsGetGlobalSettings())
    if (response?.data) apply(response.data.minimum_markup_percent)
  } finally {
    loading.value = false
  }
})

const save = async () => {
  saving.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesSettingsUpdateGlobalSettings({
        body: { minimum_markup_percent: markup.value },
      }),
    )
    if (response?.data) {
      apply(response.data.minimum_markup_percent)
      $q.notify({ type: 'positive', message: 'Minimální zisk uložen' })
    }
  } finally {
    saving.value = false
  }
}
</script>
