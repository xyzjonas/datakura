import { warehouseApiRoutesSettingsGetGlobalSettings } from '@/client'
import { computed, ref } from 'vue'

// shared by the whole app: the order screens only read it, whoever knows better (settings
// page after saving, order detail on load) feeds it
const minimumMarkupPercent = ref(0)

export const setMinimumMarkupPercent = (value: number) => {
  minimumMarkupPercent.value = value
}

export const loadMinimumMarkupPercent = async () => {
  const response = await warehouseApiRoutesSettingsGetGlobalSettings()
  if (response.data) {
    minimumMarkupPercent.value = response.data.data.minimum_markup_percent
  }
}

/** Lowest allowed přirážka (%) of outbound orders / items, 0 = no guard. */
export const useMinimumProfit = () => ({
  minimumMarkupPercent,
  enabled: computed(() => minimumMarkupPercent.value > 0),
})
