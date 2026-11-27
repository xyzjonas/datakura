<template>
  <div class="flex flex-col gap-2" data-test="norm-result">
    <div data-test="norm-result-summary">
      Zpracováno produktů {{ result.products_scanned }}: normu získalo
      <strong>{{ result.norms_linked }}</strong> (nových norem {{ result.norms_created }}, propojení
      ekvivalentů {{ result.aliases_linked }}), celní nomenklaturu
      <strong>{{ result.customs_filled }}</strong>
    </div>
    <div v-if="result.norms_kept" class="text-sm text-muted" data-test="norm-result-kept">
      Produktů s již vyplněnou normou (ponecháno beze změny): {{ result.norms_kept }}
    </div>
    <div class="text-sm" data-test="norm-result-missing">
      Stále bez normy: {{ result.without_norm }}, bez celní nomenklatury:
      {{ result.without_customs }}
    </div>

    <q-banner
      v-if="result.invalid_count"
      rounded
      class="bg-warning/20"
      data-test="norm-result-invalid"
    >
      <div class="font-semibold mb-1">
        Neplatné hodnoty ({{ result.invalid_count }})
        <span v-if="result.invalid_count > result.invalid.length" class="font-normal">
          - zobrazeno prvních {{ result.invalid.length }}
        </span>
      </div>
      <div class="max-h-64 overflow-auto text-sm">
        <div v-for="(issue, index) in result.invalid" :key="index">
          <router-link
            :to="{ name: 'productDetail', params: { productCode: issue.product_code } }"
            class="link"
            >{{ issue.product_code }}</router-link
          >
          - {{ issue.key }}: "{{ issue.value }}" ({{ issue.reason }})
        </div>
      </div>
    </q-banner>
  </div>
</template>

<script setup lang="ts">
import type { NormBackfillResultSchema } from '@/client'

defineProps<{ result: NormBackfillResultSchema }>()
</script>
