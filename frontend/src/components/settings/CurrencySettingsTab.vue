<template>
  <div>
    <h1 class="mb-2">MĚNOVÉ MOŽNOSTI</h1>
    <p class="mb-5 text-muted max-w-3xl">
      Základní měna je měna, ve které firma odvádí daně. Všechny výpočty, sklad a analytika jedou
      vždy v ní. Zákazníkovi lze nastavit jinou měnu (např. EUR) - objednávky se mu pak zobrazují a
      fakturují v ní, ale systém je pod kapotou počítá v základní měně.
    </p>

    <div class="flex flex-col gap-10">
      <section>
        <h2 class="text-lg font-semibold uppercase mb-3">Základní měna</h2>
        <q-card flat bordered class="rounded-md">
          <div class="p-4 flex flex-col gap-3">
            <q-banner v-if="baseChanged" rounded class="bg-light-orange text-orange-9">
              Změna základní měny smaže všechny zadané kurzy (jsou vztažené k základní měně).
              Stávající objednávky si ponechají svou měnu.
            </q-banner>
            <div class="flex items-center gap-3">
              <q-select
                v-model="baseCurrency"
                :options="supportedCurrencies"
                outlined
                dense
                label="Základní měna"
                class="w-64"
                hide-bottom-space
                :loading="loading"
                data-test="base-currency"
              />
              <q-btn
                unelevated
                color="primary"
                label="uložit"
                :loading="savingBase"
                :disable="!baseChanged"
                data-test="save-base-currency"
                @click="saveBase"
              />
            </div>
          </div>
        </q-card>
      </section>

      <section>
        <h2 class="text-lg font-semibold uppercase mb-3">Kurzy</h2>
        <q-card flat bordered class="rounded-md">
          <div class="p-4 flex flex-col gap-3">
            <p class="text-sm text-muted">
              Pevné kurzy (např. roční kurz vydaný centrální bankou): kolik {{ savedBase }} stojí 1
              jednotka dané měny. Kurz se při vytvoření objednávky zamkne - pozdější změna kurzu už
              existující objednávky neovlivní.
            </p>
            <div v-for="currency in foreignCurrencies" :key="currency" class="flex items-center">
              <q-input
                v-model.number="rates[currency]"
                type="number"
                outlined
                dense
                min="0"
                step="any"
                :label="`1 ${currency} =`"
                class="w-64"
                hide-bottom-space
                :loading="loading"
                :data-test="`rate-${currency}`"
              >
                <template #append>
                  <span class="text-sm">{{ savedBase }}</span>
                </template>
              </q-input>
            </div>
            <div>
              <q-btn
                unelevated
                color="primary"
                label="uložit kurzy"
                :loading="savingRates"
                :disable="!ratesValid || !ratesChanged"
                data-test="save-rates"
                @click="saveRates"
              />
            </div>
          </div>
        </q-card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesSettingsGetGlobalSettings,
  warehouseApiRoutesSettingsUpdateGlobalSettings,
  type GlobalSettingsSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { setCurrencySettings } from '@/composables/use-currency-settings'
import { useQuasar } from 'quasar'
import { computed, onMounted, ref } from 'vue'

const { onResponse } = useApi()
const $q = useQuasar()

const loading = ref(false)
const savingBase = ref(false)
const savingRates = ref(false)

const baseCurrency = ref('CZK')
const savedBase = ref('CZK')
const supportedCurrencies = ref<string[]>([])
const rates = ref<Record<string, number | null>>({})
const savedRates = ref<Record<string, number>>({})

const baseChanged = computed(() => baseCurrency.value !== savedBase.value)
const foreignCurrencies = computed(() =>
  supportedCurrencies.value.filter((currency) => currency !== savedBase.value),
)
const ratesValid = computed(() =>
  foreignCurrencies.value.every((currency) => {
    const rate = rates.value[currency]
    return rate === null || rate === undefined || (typeof rate === 'number' && rate > 0)
  }),
)
const ratesChanged = computed(() =>
  foreignCurrencies.value.some(
    (currency) => (rates.value[currency] ?? undefined) !== savedRates.value[currency],
  ),
)

const apply = (settings: GlobalSettingsSchema) => {
  baseCurrency.value = settings.base_currency
  savedBase.value = settings.base_currency
  supportedCurrencies.value = settings.supported_currencies
  savedRates.value = Object.fromEntries(settings.exchange_rates.map((r) => [r.currency, r.rate]))
  rates.value = { ...savedRates.value }
  setCurrencySettings(settings)
}

onMounted(async () => {
  loading.value = true
  try {
    const response = onResponse(await warehouseApiRoutesSettingsGetGlobalSettings())
    if (response?.data) apply(response.data)
  } finally {
    loading.value = false
  }
})

const saveBase = async () => {
  savingBase.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesSettingsUpdateGlobalSettings({
        body: { base_currency: baseCurrency.value },
      }),
    )
    if (response?.data) {
      apply(response.data)
      $q.notify({ type: 'positive', message: 'Základní měna uložena' })
    }
  } finally {
    savingBase.value = false
  }
}

const saveRates = async () => {
  savingRates.value = true
  try {
    const exchangeRates = foreignCurrencies.value
      .filter((currency) => typeof rates.value[currency] === 'number')
      .map((currency) => ({ currency, rate: rates.value[currency] as number }))
    const response = onResponse(
      await warehouseApiRoutesSettingsUpdateGlobalSettings({
        body: { exchange_rates: exchangeRates },
      }),
    )
    if (response?.data) {
      apply(response.data)
      $q.notify({ type: 'positive', message: 'Kurzy uloženy' })
    }
  } finally {
    savingRates.value = false
  }
}
</script>
