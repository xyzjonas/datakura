<template>
  <q-card flat bordered class="rounded-md">
    <div class="p-4 flex flex-col gap-3">
      <p class="text-sm text-muted max-w-3xl">
        Určuje, jak se číslují nově vytvářené doklady (objednávky, kalkulace, výrobní příkazy).
        Měsíční číslování začíná každý měsíc od 1 (např. OP2026110003), roční jednou za rok (např.
        OP202600003). Již vytvořené doklady se nemění.
      </p>
      <div class="flex items-center gap-3">
        <q-select
          v-model="codeSequence"
          :options="options"
          emit-value
          map-options
          outlined
          dense
          label="Číslování dokladů"
          class="w-64"
          :loading="loading"
        />
        <q-btn
          unelevated
          color="primary"
          label="uložit"
          :loading="saving"
          :disable="codeSequence === savedValue"
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
  type CodeSequence,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { onMounted, ref } from 'vue'

const { onResponse } = useApi()

const options: { label: string; value: CodeSequence }[] = [
  { label: 'Roční (nové číslo každý rok)', value: 'yearly' },
  { label: 'Měsíční (nové číslo každý měsíc)', value: 'monthly' },
]

const codeSequence = ref<CodeSequence>('yearly')
const savedValue = ref<CodeSequence>('yearly')
const loading = ref(false)
const saving = ref(false)

const apply = (value: CodeSequence) => {
  codeSequence.value = value
  savedValue.value = value
}

onMounted(async () => {
  loading.value = true
  try {
    const response = onResponse(await warehouseApiRoutesSettingsGetGlobalSettings())
    if (response?.data) apply(response.data.code_sequence)
  } finally {
    loading.value = false
  }
})

const save = async () => {
  saving.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesSettingsUpdateGlobalSettings({
        body: { code_sequence: codeSequence.value },
      }),
    )
    if (response?.data) apply(response.data.code_sequence)
  } finally {
    saving.value = false
  }
}
</script>
