import { warehouseApiRoutesSettingsGetGlobalSettings, type GlobalSettingsSchema } from '@/client'
import { computed, ref } from 'vue'

const DEFAULT_CURRENCIES = ['CZK', 'EUR', 'PLN']

// shared by the whole app, same as the minimum profit: screens only read it, whoever knows
// better (settings page after saving, app start) feeds it
const baseCurrency = ref('CZK')
const supportedCurrencies = ref<string[]>(DEFAULT_CURRENCIES)
let loaded = false

export const setCurrencySettings = (
  settings: Pick<GlobalSettingsSchema, 'base_currency' | 'supported_currencies'>,
) => {
  baseCurrency.value = settings.base_currency
  supportedCurrencies.value = settings.supported_currencies
  loaded = true
}

export const loadCurrencySettings = async (force = false) => {
  if (loaded && !force) {
    return
  }
  try {
    const response = await warehouseApiRoutesSettingsGetGlobalSettings()
    if (response.data) {
      setCurrencySettings(response.data.data)
    }
  } catch {
    // the defaults (CZK + the supported list) keep the UI usable, next mount retries
  }
}

/** The currency the company does its taxes in + the currencies the app can work with. */
export const useCurrencySettings = () => {
  void loadCurrencySettings()
  return {
    baseCurrency,
    supportedCurrencies,
    currencies: computed(() => supportedCurrencies.value),
  }
}
