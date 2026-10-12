<template>
  <q-card flat bordered class="rounded-md">
    <div class="p-4 flex flex-col gap-3">
      <p class="text-sm text-muted">
        Pokud je celková cena položky objednávky nebo kalkulace nižší než tato hodnota, automaticky
        se zvýší na minimum. Zákazník může mít vlastní hodnotu, nebo může být zaokrouhlování u něj
        vypnuto. 0 = bez minima.
      </p>
      <div class="flex items-center gap-3">
        <q-input
          v-model.number="minimumItemValue"
          type="number"
          outlined
          dense
          min="0"
          label="Minimální hodnota položky"
          class="w-64"
          :loading="loading"
        />
        <q-btn
          unelevated
          color="primary"
          label="uložit"
          :loading="saving"
          :disable="!isValid || minimumItemValue === savedValue"
          @click="save"
        />
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesSettingsGetGlobalSettings,
  warehouseApiRoutesSettingsUpdateGlobalSettings,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { computed, onMounted, ref } from 'vue'

const { onResponse } = useApi()

const minimumItemValue = ref(0)
const savedValue = ref(0)
const loading = ref(false)
const saving = ref(false)

const isValid = computed(
  () => typeof minimumItemValue.value === 'number' && minimumItemValue.value >= 0,
)

const apply = (value: number) => {
  minimumItemValue.value = value
  savedValue.value = value
}

onMounted(async () => {
  loading.value = true
  try {
    const response = onResponse(await warehouseApiRoutesSettingsGetGlobalSettings())
    if (response?.data) apply(response.data.minimum_item_value)
  } finally {
    loading.value = false
  }
})

const save = async () => {
  saving.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesSettingsUpdateGlobalSettings({
        body: { minimum_item_value: minimumItemValue.value },
      }),
    )
    if (response?.data) apply(response.data.minimum_item_value)
  } finally {
    saving.value = false
  }
}
</script>
